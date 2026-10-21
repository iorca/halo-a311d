#!/usr/bin/env python3
"""
校验编译出的 DTB 里，每个 CPU 实际使用的 OPP 表与上游定义一致。

背景
----
本仓库的板级 DTS 曾经同时 include 了 meson-g12b-a311d.dtsi 和
meson-g12b-s922x.dtsi。两者都在根节点下定义**同名**节点 opp-table-0 /
opp-table-1（label 也同名：cpu_opp_table_0 / cpub_opp_table_1），
但电压值不同：

    a311d: 1.0 GHz = 761000 uV
    s922x: 1.0 GHz = 731000 uV

dtc 对同名节点是**合并**而非报错（livetree.c: merge_nodes()）：
后定义的属性覆盖先定义的，同名子节点取并集。
结果是 CPU 拿到一张「A311D + S922X 混搭」的频率-电压表，
还混进了 A311D 不支持的频率点（1.896 / 1.992 GHz）。

dtc 自己不报错：合并后树里已无重名节点，duplicate_node_names /
duplicate_label 两道 ERROR 级检查都不触发，**退出码是 0，CI 全绿**。
所以只能显式比对产物。

校验的不变式
------------
**期望值一律取自上游，不采信被测板级 DTS 自己的声明。**

  · 表的内容    → 上游 meson-g12b-a311d.dtsi（label cpu_opp_table_0 / cpub_opp_table_1）
  · CPU 该用哪张表 → 上游板级 dtsi（&cpuN 的 operating-points-v2）

上游把「CPU 用哪张表」放在哪个文件随内核版本变动：
  v6.18  → meson-g12b-khadas-vim3.dtsi
  master → meson-g12b-a311d.dtsi 自己
所以参考文件给多个，脚本在全部里一起找。

对每个 CPU：DTB 里它实际引用的那张表，内容必须与上游对应表**逐项相同**。

这个不变式同时抓住三类错误：
  1. 多个 SoC dtsi 被合并 → 表内容被污染
  2. 板级把 CPU 指到了错误的表（A53 误指大核表）→ 内容对不上
  3. 板级把表改名 → 按内容比对，不受影响

若拿「板级 DTS 自己的声明」当期望值，第 2 类就永远发现不了
（板级说 cpu0 用 A 表，DTB 里 cpu0 确实用 A 表，自洽但都是错的）。

用法
----
    check-opp-tables.py <编译出的 .dtb> <上游参考 dtsi> [更多参考 dtsi...]

例：
    check-opp-tables.py out.dtb \
        $D/meson-g12b-a311d.dtsi $D/meson-g12b-khadas-vim3.dtsi

退出码
------
    0  一致
    1  不一致（打印差异）
    2  用法错误 / 文件缺失 / 无法解析
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


def cpu_table_content(props, kids, cpu):
    """某个 cpu 节点实际引用的 OPP 表 → (表节点路径, 表内容)

    板级 dts 里用 &cpu0 这样的 label 引用，DTB 里的节点名却是 cpu@0。
    这里按 CPU 编号匹配：cpu0 → cpu@0、cpu100 → cpu@100。
    """
    ph2path = {}
    for path, plist in props.items():
        for name, val in plist:
            if name == "phandle":
                ph2path[int.from_bytes(val, "big")] = path

    num = cpu[3:]  # 去掉 "cpu" 前缀
    for cand in (f"cpu@{num}", cpu):
        for name, val in props.get(f"/cpus/{cand}", []):
            if name == "operating-points-v2" and len(val) == 4:
                path = ph2path.get(int.from_bytes(val, "big"))
                if path is None:
                    return None, None
                return path, dtb_opp_table(props, kids, path.lstrip("/"))
    return None, None


# --------------------------------------------------------------------------
# 文本解析：板级 dts 与上游 dtsi
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
    """从 dtsi 文本提取 label 所指的 OPP 表 → (节点名, {频率Hz: 电压µV})

    上游写法形如：
        cpu_opp_table_0: opp-table-0 { ... }
    label 与节点名不同，这里按 label 定位并取其节点名。
    """
    m = re.search(re.escape(label) + r"\s*:\s*([A-Za-z0-9_-]+)\s*\{", text)
    if not m:
        raise KeyError(f"找不到 label {label}")
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


def cpu_opp_label_refs(text):
    """从板级 dtsi 解析每个 &cpuN 声明的 OPP 表 label → {cpu: label}

    形如：
        &cpu0 {
            ...
            operating-points-v2 = <&cpu_opp_table_0>;
            ...
        };
    """
    refs = {}
    for m in re.finditer(r"&(cpu\d+)\s*\{", text):
        cpu = m.group(1)
        block = _extract_block(text, m.end() - 1)
        for om in re.finditer(r"operating-points-v2\s*=\s*<&([A-Za-z0-9_]+)>", block):
            refs[cpu] = om.group(1)
    return refs


# --------------------------------------------------------------------------
# 对比与报告
# --------------------------------------------------------------------------
def fmt_table(tbl):
    if not tbl:
        return "    (空)"
    return "\n".join(
        f"    {hz / 1e9:>7.3f} GHz  {uv:>7} µV" for hz, uv in sorted(tbl.items())
    )


def diff_tables(expected, actual):
    """返回描述差异的若干行"""
    lines = []
    only_exp = sorted(set(expected) - set(actual))
    only_act = sorted(set(actual) - set(expected))
    if only_exp:
        lines.append("    缺少（上游有）: "
                     + ", ".join(f"{hz / 1e9:g}GHz@{expected[hz]}uV" for hz in only_exp))
    if only_act:
        lines.append("    多出（上游没有）: "
                     + ", ".join(f"{hz / 1e9:g}GHz@{actual[hz]}uV" for hz in only_act))
    diff = [hz for hz in sorted(set(expected) & set(actual)) if expected[hz] != actual[hz]]
    if diff:
        lines.append("    电压不同: " + ", ".join(
            f"{hz / 1e9:g}GHz(上游 {expected[hz]}uV / DTB {actual[hz]}uV)" for hz in diff))
    return lines


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    dtb_path = argv[1]
    ref_paths = argv[2:]

    try:
        dtb = open(dtb_path, "rb").read()
        refs = [(p, open(p, encoding="utf-8", errors="replace").read())
                for p in ref_paths]
    except OSError as e:
        print(f"::error::读文件失败: {e}")
        return 2

    try:
        props, kids = parse_fdt(dtb)
    except ValueError as e:
        print(f"::error::解析 DTB 失败 {dtb_path}: {e}")
        return 2

    print(f"DTB     : {dtb_path}")
    for p, _ in refs:
        print(f"参考    : {p}")

    # 上游：CPU → 应使用哪张表（在所有参考文件里一起找）
    want = {}
    for p, text in refs:
        try:
            for cpu, label in cpu_opp_label_refs(text).items():
                want.setdefault(cpu, label)
        except ValueError as e:
            print(f"::error::解析 {p} 失败: {e}")
            return 2
    if not want:
        print("::error::上游参考里找不到 operating-points-v2 声明，无法校验")
        return 2

    # 上游：每张表的内容（同样在所有参考文件里找）
    up_tables = {}
    for label in sorted(set(want.values())):
        for p, text in refs:
            try:
                up_tables[label] = dtsi_opp_table(text, label)
                break
            except KeyError:
                continue
        if label not in up_tables:
            print(f"::error::在参考文件里找不到 OPP 表 {label}")
            return 2

    ok = True
    for cpu, label in sorted(want.items(), key=lambda kv: int(kv[0][3:])):
        up_node, expected = up_tables[label]
        table, actual = cpu_table_content(props, kids, cpu)
        if table is None:
            print(f"  ❌ {cpu}: DTB 里没有 operating-points-v2 引用")
            ok = False
            continue

        if actual == expected:
            print(f"  ✅ {cpu} → {table}（应为 {label} = {up_node}，{len(actual)} 项）与上游一致")
            continue

        print(f"  ❌ {cpu} → {table}（应为 {label} = {up_node}）与上游不一致")
        for line in diff_tables(expected, actual):
            print(line)
        print(f"    上游 {up_node}（{label}）:")
        print(fmt_table(expected).replace("\n", "\n    "))
        print(f"    DTB  {table}:")
        print(fmt_table(actual).replace("\n", "\n    "))
        ok = False

    if not ok:
        print()
        print("::error::CPU 使用的 OPP 表与上游 A311D 定义不一致。")
        print("::error::常见原因：")
        print("::error::  a) 板级 DTS 同时 include 了多份 SoC 的 dtsi")
        print("::error::     （如 meson-g12b-s922x.dtsi）→ dtc 把同名 opp-table 合并成混搭表")
        print("::error::  b) 板级把 CPU 的 operating-points-v2 指到了错误的表")
        print("::error::本板是 A311D，只应 include meson-g12b-a311d.dtsi 一份。")
    else:
        print()
        print(f"OK  {len(want)} 个 CPU 的 OPP 表均与上游 A311D 定义一致")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
