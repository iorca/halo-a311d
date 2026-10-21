#!/usr/bin/env python3
"""
校验编译出的 DTB 里的 CPU OPP 表与上游 meson-g12b-a311d.dtsi 完全一致。

背景
----
本仓库的板级 DTS 曾经同时 include 了 meson-g12b-a311d.dtsi 和
meson-g12b-s922x.dtsi。两者都在根节点下定义**同名**节点 opp-table-0 /
opp-table-1（label 也同名：cpu_opp_table_0 / cpub_opp_table_1），
但电压值不同。

dtc 对同名节点是**合并**而非报错（livetree.c: merge_nodes()）：
后定义的属性覆盖先定义的，同名子节点取并集。
结果是 CPU 拿到一张「A311D + S922X 混搭」的频率-电压表，
还混进了 A311D 不支持的频率点（1.896 / 1.992 GHz）。

dtc 自己不报错（合并后树里已无重名节点，duplicate_node_names / duplicate_label
两道 ERROR 级检查都不触发），所以只靠 dtc 退出码的 CI 永远看不见这个问题。
本脚本就是那道缺失的护栏。

用法
----
    check-opp-tables.py <编译出的 .dtb> <meson-g12b-a311d.dtsi>

    要校验哪张表不用指定：脚本顺着 CPU 节点的 operating-points-v2
    phandle 反查 CPU **实际**在用的表（板级 DTS 可以给表改名），
    再与上游 dtsi 里的 cpu_opp_table_0 / cpub_opp_table_1 逐项比对。

退出码
------
    0  一致
    1  不一致（并打印差异）
    2  用法错误 / 文件缺失
"""

import re
import struct
import sys

# --------------------------------------------------------------------------
# DTB（扁平设备树二进制）解析
# --------------------------------------------------------------------------
def parse_fdt(dtb):
    """返回 (props, kids)

    props: {节点路径: [(属性名, 字节值)]}
    kids:  {节点路径: [子节点名]}
    """
    if len(dtb) < 40 or dtb[:4] != b"\xd0\x0d\xfe\xed":
        raise ValueError("不是合法的 DTB（magic 不匹配）")

    hdr = struct.unpack(">10I", dtb[:40])
    off_struct, off_strings = hdr[2], hdr[3]
    size_strings, size_struct = hdr[8], hdr[9]
    strings = dtb[off_strings:off_strings + size_strings]
    sd = dtb[off_struct:off_struct + size_struct]

    def s(off):
        end = strings.index(b"\x00", off)
        return strings[off:end].decode()

    props, kids = {}, {}
    path = []
    i = 0
    while i < len(sd):
        tok = struct.unpack(">I", sd[i:i + 4])[0]
        i += 4
        if tok == 1:  # FDT_BEGIN_NODE
            end = sd.index(b"\x00", i)
            name = sd[i:end].decode()
            i = (end + 4) & ~3
            path.append(name)
            if len(path) > 1:
                kids.setdefault("/".join(path[:-1]), []).append(name)
        elif tok == 2:  # FDT_END_NODE
            path.pop()
        elif tok == 3:  # FDT_PROP
            plen, noff = struct.unpack(">II", sd[i:i + 8])
            i += 8
            val = sd[i:i + plen]
            i = (i + plen + 3) & ~3
            cur = "/" + "/".join(x for x in path if x)
            props.setdefault(cur, []).append((s(noff), val))
        elif tok == 4:  # FDT_NOP
            pass
        elif tok == 9:  # FDT_END
            break
        else:
            raise ValueError(f"非法的 FDT token {tok}")
    return props, kids


def dtb_opp_table(props, kids, table):
    """从 DTB 提取某张 OPP 表 → {频率Hz: 电压µV}"""
    out = {}
    for child in kids.get("/" + table, []):
        hz = uv = None
        for name, val in props.get(f"/{table}/{child}", []):
            if name == "opp-hz" and len(val) in (4, 8):
                hz = int.from_bytes(val, "big")
            elif name == "opp-microvolt" and len(val) == 4:
                uv = int.from_bytes(val, "big")
        if hz is not None:
            out[hz] = uv
    return out


def cpu_opp_tables(props, kids):
    """从 CPU 节点反查它实际引用的 OPP 表 → {表节点路径: [cpu 节点名]}

    不能直接假设表叫 /opp-table-0 —— 板级 DTS 可以把 CPU 指向任意名字的表。
    这里顺着 operating-points-v2 的 phandle 走，得到 CPU **真正**在用的表。
    """
    ph2path = {}
    for path, plist in props.items():
        for name, val in plist:
            if name == "phandle":
                ph2path[int.from_bytes(val, "big")] = path

    used = {}
    for cpu in kids.get("/cpus", []):
        if not cpu.startswith("cpu@"):
            continue
        for name, val in props.get(f"/cpus/{cpu}", []):
            if name != "operating-points-v2" or len(val) != 4:
                continue
            target = ph2path.get(int.from_bytes(val, "big"))
            if target:
                used.setdefault(target, []).append(cpu)
    return used


# --------------------------------------------------------------------------
# 上游 dtsi 文本解析
# --------------------------------------------------------------------------
# opp-hz 既可能写成 <1000000000>，也可能写成 /bits/ 64 <1000000000>
RE_HZ = re.compile(r"opp-hz\s*=\s*(?:/bits/\s*\d+\s*)?<\s*(\d+)\s*>")
RE_UV = re.compile(r"opp-microvolt\s*=\s*<\s*(\d+)\s*>")
RE_ENTRY = re.compile(r"opp-(\d+)\s*\{")


def _extract_block(text, start):
    """从 '{' 处取出配对的大括号块（含首尾括号）"""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise ValueError("大括号不配对")


def dtsi_opp_table(text, label):
    """从 dtsi 文本提取某张 OPP 表 → (节点名, {频率Hz: 电压µV})

    上游写法形如：
        cpu_opp_table_0: opp-table-0 { ... }
    label 与节点名不同，这里按 label 定位并取其节点名。
    """
    m = re.search(re.escape(label) + r"\s*:\s*([A-Za-z0-9_-]+)\s*\{", text)
    if not m:
        raise KeyError(f"dtsi 里找不到 label {label}")
    node_name = m.group(1)
    block = _extract_block(text, m.end() - 1)

    out = {}
    for em in RE_ENTRY.finditer(block):
        hz = int(em.group(1))
        sub = _extract_block(block, em.end() - 1)
        um = RE_UV.search(sub)
        if um:
            out[hz] = int(um.group(1))
    return node_name, dict(sorted(out.items()))


# --------------------------------------------------------------------------
# 对比与报告
# --------------------------------------------------------------------------
def fmt_table(tbl):
    if not tbl:
        return "    (空)"
    return "\n".join(
        f"    {hz / 1e9:>7.3f} GHz  {uv:>7} µV" for hz, uv in sorted(tbl.items())
    )


def compare(name, expected, actual):
    """返回 (是否一致, 报告文本)"""
    if expected == actual:
        return True, f"  ✅ {name}: {len(actual)} 项，与上游一致"

    lines = [f"  ❌ {name}: 与上游不一致（上游 {len(expected)} 项 / DTB {len(actual)} 项）"]

    only_exp = sorted(set(expected) - set(actual))
    only_act = sorted(set(actual) - set(expected))
    if only_exp:
        lines.append(f"    DTB 缺少（上游独有）: "
                     + ", ".join(f"{hz / 1e9:g}GHz@{expected[hz]}uV" for hz in only_exp))
    if only_act:
        lines.append(f"    DTB 多出（上游没有）: "
                     + ", ".join(f"{hz / 1e9:g}GHz@{actual[hz]}uV" for hz in only_act))
    diff = [hz for hz in sorted(set(expected) & set(actual)) if expected[hz] != actual[hz]]
    if diff:
        lines.append("    电压不同: " + ", ".join(
            f"{hz / 1e9:g}GHz(上游 {expected[hz]}uV / DTB {actual[hz]}uV)" for hz in diff))

    lines.append("    上游: " + fmt_table(expected).replace("\n", "\n    "))
    lines.append("    DTB : " + fmt_table(actual).replace("\n", "\n    "))
    return False, "\n".join(lines)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    dtb_path, dtsi_path = argv[1], argv[2]
    if len(argv) > 3:
        print("::error::本脚本不需要表名参数（表由 CPU 的 operating-points-v2 反查得出）")
        return 2

    try:
        dtb = open(dtb_path, "rb").read()
    except OSError as e:
        print(f"::error::读不到 DTB {dtb_path}: {e}")
        return 2
    try:
        dtsi = open(dtsi_path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"::error::读不到 dtsi {dtsi_path}: {e}")
        return 2

    try:
        props, kids = parse_fdt(dtb)
    except ValueError as e:
        print(f"::error::解析 DTB 失败 {dtb_path}: {e}")
        return 2

    print(f"DTB  : {dtb_path}")
    print(f"参考 : {dtsi_path}")

    # CPU 实际引用的表（顺着 operating-points-v2 的 phandle 反查）
    used = cpu_opp_tables(props, kids)
    if not used:
        print("::error::DTB 里找不到 CPU 的 operating-points-v2 引用，无法校验 OPP 表")
        return 2
    print("CPU 引用的 OPP 表: " + ", ".join(
        f"{t} ({len(c)} 个 cpu: {', '.join(sorted(c))})" for t, c in sorted(used.items())))

    # 上游 dtsi 里按 label 找表：cpu_opp_table_0 / cpub_opp_table_1
    upstream_tables = {}
    for label in ("cpu_opp_table_0", "cpub_opp_table_1"):
        try:
            node_name, table = dtsi_opp_table(dtsi, label)
        except (KeyError, ValueError) as e:
            print(f"::error::解析上游 {label} 失败: {e}")
            return 2
        upstream_tables[label] = (node_name, table)

    ok = True
    # 上游两张表分别对应 DTB 里的哪张：
    #   DTB 的表名可能与上游不同（板级可改名），所以先按表名对上，
    #   对不上再按内容匹配。
    unmatched = list(used.items())
    for label, (up_node, expected) in upstream_tables.items():
        name_hits = [t for t in unmatched if t[0].rsplit("/", 1)[-1] == up_node]
        content_hits = [t for t in unmatched
                        if dtb_opp_table(props, kids, t[0].lstrip("/")) == expected]
        candidates = name_hits or content_hits
        if not candidates:
            print(f"  ❌ {label}: DTB 中找不到与上游对应的表")
            print("    上游: " + fmt_table(expected).replace("\n", "\n    "))
            ok = False
            continue
        table, cpus = candidates[0]
        unmatched.remove((table, cpus))
        actual = dtb_opp_table(props, kids, table.lstrip("/"))
        same, report = compare(f"{label} → {table}", expected, actual)
        print(report)
        if not same:
            ok = False

    # DTB 里 CPU 引用了、但没对上任何一张上游表的
    for table, cpus in unmatched:
        actual = dtb_opp_table(props, kids, table.lstrip("/"))
        print(f"  ❌ {table}: CPU（{', '.join(sorted(cpus))}）在用这张表，"
              f"但它与上游任何一张 OPP 表都不一致")
        print("    DTB : " + fmt_table(actual).replace("\n", "\n    "))
        ok = False

    if not ok:
        print()
        print("::error::CPU OPP 表与上游 A311D 定义不一致。")
        print("::error::常见原因：板级 DTS 同时 include 了多份 SoC 的 dtsi")
        print("::error::（如 meson-g12b-s922x.dtsi），dtc 会把它们**合并**成混搭表。")
        print("::error::本板是 A311D，只应 include meson-g12b-a311d.dtsi 一份。")
    else:
        print()
        print("OK  CPU OPP 表与上游 A311D 定义一致")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
