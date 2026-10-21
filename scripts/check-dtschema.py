#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 dt-validate（内核 device-tree schema 校验）的输出做筛选，只让**真问题**失败。

背景
----
内核自带一套 device-tree schema 校验工具（dt-schema，仓库
devicetree-org/dt-schema），上游用它跑 `make dtbs_check`。
它能抓的是「属性名写错 / 必填属性缺失 / 极性写反」这类
**编译期完全查不出来、运行期才暴露**的问题 —— 正是本仓库反复踩的坑
（LED 的 trigger 属性名、gpio-hog 的属性名与位置）。

为什么需要本脚本
----------------
dt-validate 直接跑会报两类噪音：

1. **本板没有对应的 schema 文件**。
   本板根节点写的是 `compatible = "althea,a311d", "amlogic,a311d", "amlogic,g12b"`，
   其中 `althea,a311d` 是自研板级 ID，上游没有它的 schema →
   dt-validate 会把根节点的 compatible 报成
   "'althea,a311d' is not one of [...]"，一次报几十行。
   这不是本板的问题，是「自研板还没有 schema」的固有情况。

2. **上游 SoC 节点的 schema 覆盖不全**。
   DTB 里包含 meson-g12-common.dtsi 引入的数百个上游节点，
   有些没有 schema 或 schema 与实际用法不完全一致。

所以：跑 dt-validate，把它的 JSON 输出交给本脚本判定 ——
只对**本板自己写的节点**（根节点的子节点）报错。

判定规则
--------
· 诊断级别为 error
· 且出问题的节点**不是根节点本身**（根节点的 compatible 匹配失败予以豁免）
→ 判定为失败。

用法
----
    dt-validate -s <内核 bindings 目录> --json-output <out.json> <dtb>
    check-dtschema.py <out.json>

退出码
------
    0  没有需要关注的 error（豁免项除外）
    1  有真问题
    2  用法错误 / JSON 读不了
"""

import io
import json
import sys

# 豁免：根节点自身的 compatible 匹配失败。
#
# 根节点的 compatible 里有本板自研 ID（althea,a311d），上游没有对应 schema，
# dt-validate 必然报 "'althea,a311d' is not one of [...]"。
# 这是「自研板还没提交 schema 到上游」的固有情况，不是本板配置错误。
#
# 一旦本板把自己的 schema 提交到上游
# （Documentation/devicetree/bindings/board/althea,a311d.yaml），
# 这条豁免就可以去掉了 —— 届时根节点也应该被真正校验。
EXEMPT_NODES = ("/",)

# 豁免：诊断类型。
# 'unmatched' = compatible 没匹配到任何 schema（由 -c 选项产生），
# 属于"没 schema 可校验"，不是"校验不通过"。
EXEMPT_TYPES = ("unmatched",)


def collect(diagnostics, exempt_nodes):
    """挑出需要关注的 error 级诊断"""
    bad = []
    for d in diagnostics:
        if d.get("level") != "error":
            continue
        if d.get("type") in EXEMPT_TYPES:
            continue
        node = d.get("node")
        if node in exempt_nodes:
            continue
        bad.append(d)
    return bad


def fmt(d):
    node = d.get("node") or "<unknown>"
    nodename = d.get("nodename") or ""
    msg = (d.get("message") or "").split("\n")[0]
    prop = d.get("property_path") or []
    where = node
    if nodename and nodename != node.rsplit("/", 1)[-1]:
        where = "%s (%s)" % (node, nodename)
    p = " → ".join(str(x) for x in prop) if prop else ""
    return "%s: %s%s" % (where, msg, ("  [属性: %s]" % p) if p else "")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]
    try:
        with io.open(path, encoding="utf-8") as fh:
            diagnostics = json.load(fh)
    except (OSError, ValueError) as e:
        print("读不了 %s: %s" % (path, e))
        return 2

    if not isinstance(diagnostics, list):
        print("%s 的内容不是 diagnostic 数组" % path)
        return 2

    total_err = sum(1 for d in diagnostics if d.get("level") == "error")
    bad = collect(diagnostics, EXEMPT_NODES)

    print("dt-schema 校验结果：%s" % path)
    print("  诊断总数 %d，其中 error 级 %d，豁免后需关注 %d"
          % (len(diagnostics), total_err, len(bad)))

    if not bad:
        print("  ✓ 没有需要关注的错误")
        print("    （根节点 compatible 匹配失败已豁免 —— 本板自研 ID 无上游 schema）")
        return 0

    print("")
    print("发现 %d 处 schema 校验错误：" % len(bad))
    for d in bad:
        print("  ✗ " + fmt(d))
    print("")
    print("这类问题编译期查不出来（dtc 只做语法检查），运行期才会暴露。")
    print("常见原因：属性名写错（注意内核实际读的是哪个名字）、")
    print("必填属性缺失、极性写反。")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
