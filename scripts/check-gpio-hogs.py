#!/usr/bin/env python3
"""
校验编译出的 DTB 里，每个 gpio-hog 都是内核真正认的形式。

背景
----
本仓库的板级 DTS 曾经这样写 FUSB340 SEL 的 hog：

    fusb340_hog {                          /* ← 挂在根节点下 */
        gpio-hog-controller-gpios = <&gpio GPIOA_2 GPIO_ACTIVE_HIGH>;
        line-name = "FUSB340_SEL";
    };

三处都是错的，且**每一处都静默失效**：

1. `gpio-hog-controller-gpios` 这个属性在 torvalds/linux **全树搜索 0 命中**。
   上游真正的属性叫 `gpios`。
2. 节点挂在**根节点**下。内核只在 gpio controller 自己的子节点里扫 hog
   （drivers/gpio/gpiolib-of.c: of_gpiochip_scan_gpios() 遍历
   dev_of_node(&chip->gpiodev->dev) 的子节点）→ 根节点下的东西它根本不看。
3. 没有 `gpio-hog` 这个 bool 属性 → 内核不认为这是个 hog。

结果：DTB 里带着一个内核完全不认的节点，而**没有一行报错**。
编译通过、CI 全绿、产物是错的。

第 4 处错误更隐蔽：of_parse_own_gpio() 要求 input / output-low / output-high
**三选一必须显式写**，否则

    pr_warn("GPIO line %d (%pOFn): no hogging state specified, bailing out\\n", ...)
    return ERR_PTR(-EINVAL);

→ 内核**跳过该 hog**。注意这不是"自动变成 input hog"，
   不写状态属性 = 这个 hog 压根不存在。

校验的不变式
------------
对 DTB 里每一个带 `gpio-hog` 属性的节点：
  1. 它的父节点必须带 `gpio-controller`（即必须是 controller 的子节点）
  2. 必须有 `gpios` 属性
  3. 必须有 input / output-low / output-high 之一
  4. 不得出现 `gpio-hog-controller-gpios` 这种内核不存在的属性
另外，全树不得出现 `gpio-hog-controller-gpios`。

用法
----
    check-gpio-hogs.py <编译出的 .dtb>

退出码
------
    0  全部 hog 合法
    1  发现问题（逐条打印）
    2  用法错误 / 文件缺失 / 无法解析
"""

import struct
import sys

FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9

# 内核认的状态属性（三选一）
STATE_PROPS = ("input", "output-low", "output-high")
# 上游不存在的属性（本仓库曾经误用）
BOGUS_PROPS = ("gpio-hog-controller-gpios",)


def parse_fdt(dtb):
    """返回 (props, kids)

    props: {路径: [(属性名, 字节值)]}
    kids:  {路径: [子节点名]}
    """
    if len(dtb) < 40:
        raise ValueError("文件太短，不是合法 FDT")
    hdr = struct.unpack(">10I", dtb[:40])
    magic = hdr[0]
    if magic not in (0xD00DFEED, 0xD00DFDED):  # 后者含 size 字段变体
        raise ValueError("FDT magic 不对: 0x%08x" % magic)
    off_struct, off_strings = hdr[2], hdr[3]
    size_strings, size_struct = hdr[8], hdr[9]
    if off_struct + size_struct > len(dtb) or off_strings + size_strings > len(dtb):
        raise ValueError("FDT 头部给出的偏移越界")
    strings = dtb[off_strings:off_strings + size_strings]
    sd = dtb[off_struct:off_struct + size_struct]

    def s(off):
        if off >= len(strings):
            raise ValueError("字符串区偏移越界")
        end = strings.find(b"\x00", off)
        if end < 0:
            raise ValueError("字符串未终止")
        return strings[off:end].decode("utf-8", "replace")

    props, kids = {}, {}
    path, i = [], 0
    while i + 4 <= len(sd):
        tok = struct.unpack(">I", sd[i:i + 4])[0]
        i += 4
        if tok == FDT_BEGIN_NODE:
            end = sd.find(b"\x00", i)
            if end < 0:
                raise ValueError("节点名未终止")
            name = sd[i:end].decode("utf-8", "replace")
            i = (end + 4) & ~3
            path.append(name)
            if len(path) > 1:
                kids.setdefault("/".join(path[:-1]), []).append(name)
        elif tok == FDT_END_NODE:
            if not path:
                raise ValueError("END_NODE 多于 BEGIN_NODE")
            path.pop()
        elif tok == FDT_PROP:
            if i + 8 > len(sd):
                raise ValueError("PROP 头越界")
            plen, noff = struct.unpack(">II", sd[i:i + 8])
            i += 8
            if i + plen > len(sd):
                raise ValueError("属性值越界")
            val = sd[i:i + plen]
            i = (i + plen + 3) & ~3
            cur = "/" + "/".join(x for x in path if x)
            props.setdefault(cur, []).append((s(noff), val))
        elif tok == FDT_NOP:
            continue
        elif tok == FDT_END:
            break
        else:
            raise ValueError("未知 FDT token: %d" % tok)
    return props, kids


def prop_names(props, path):
    return [n for n, _ in props.get(path, [])]


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        with open(argv[1], "rb") as fh:
            dtb = fh.read()
    except OSError as e:
        print("读不了 %s: %s" % (argv[1], e))
        return 2

    try:
        props, kids = parse_fdt(dtb)
    except ValueError as e:
        print("解析 FDT 失败: %s" % e)
        return 2

    problems = []

    # ---- 检查 1：全树不得出现内核不存在的 hog 属性 ----
    for path, plist in props.items():
        for name, _ in plist:
            if name in BOGUS_PROPS:
                problems.append(
                    "%s: 出现内核**不存在**的属性 `%s`（上游真正用的是 `gpios`）"
                    % (path, name))

    # ---- 检查 2~4：每一个 gpio-hog 节点都要合法 ----
    hogs = 0
    for path, plist in props.items():
        names = prop_names(props, path)
        if "gpio-hog" not in names:
            continue
        hogs += 1

        # 2. 父节点必须是 gpio-controller
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        parent_names = prop_names(props, parent) if parent else []
        if "gpio-controller" not in parent_names:
            problems.append(
                "%s: hog 不在 gpio-controller 的子节点下（父节点 `%s` 没有 "
                "gpio-controller）→ 内核 of_gpiochip_scan_gpios() 根本不会扫它"
                % (path, parent or "<根>"))

        # 3. 必须有 gpios
        if "gpios" not in names:
            problems.append("%s: hog 缺少 `gpios` 属性" % path)

        # 4. 必须有 input / output-low / output-high 之一
        if not any(x in names for x in STATE_PROPS):
            problems.append(
                "%s: hog 没有指定状态（input / output-low / output-high 三选一"
                "必须显式写）→ 内核会打印 \"no hogging state specified, bailing "
                "out\" 并**跳过该 hog**（不是自动变成 input）" % path)

    print("检查 %s：%d 个 gpio-hog" % (argv[1], hogs))
    if problems:
        print("发现问题 %d 处：" % len(problems))
        for p in problems:
            print("  ✗ " + p)
        return 1
    print("  ✓ 全部 gpio-hog 均为内核认可的形式")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
