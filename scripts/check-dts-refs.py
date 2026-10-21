#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板级 DTS 的 label 引用完整性检查。

为什么需要它
------------
dtc 的 `path_references` 检查（ERROR 级）只能发现**根节点路径**形式的悬空引用，
而 DTS 里最常见的悬空引用是 `&label` 形式：

    aliases {
        rtc0 = &rtc;      /* &rtc 若没有对应 label → 编译期 ERROR */
    };

这类错误**只有编译时才会暴露**。而本仓库曾因为删掉一个节点（rtc@51）却忘了
改 aliases 里的 `&rtc` 引用，导致 CI 变红 —— 靠的就是 dtc 的这道检查。
但 dtc 每次要拉整个内核树才能跑，本地跑不了。

所以本脚本做**离线**的等价检查：
  1. 收集板级 DTS 及其 include 链里定义的全部 label
  2. 收集板级 DTS 里引用的全部 &label
  3. 报告「引用了但没定义」的 label

include 链的 label 用「从上游 dtsi 里正则抽取」的方式收集 ——
上游 dtsi 的 label 都是 `name: node {` 或 `name: node@addr {` 这种形式，
正则足够可靠。

用法：
    python3 scripts/check-dts-refs.py <板级 dts> [上游 dtsi 目录]
"""
import io
import os
import re
import sys

# 板级 dts 里 include 的 SoC 级 dtsi（只允许 a311d 这一份）
SOC_DTSI = "meson-g12b-a311d.dtsi"

# 上游 dtsi 里 label 的定义形式：
#     foo: node@1234 {        /     foo: node {
LABEL_DEF = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[A-Za-z_@]", re.M)
# 引用形式 &foo  （排除 &foo_path 这种在字符串里的，以及 &{...}）
LABEL_REF = re.compile(r"&([A-Za-z_][A-Za-z0-9_]*)")
# 注释
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"//[^\n]*")


def strip_comments(text):
    """去掉注释（保留行数，方便报错定位）"""
    text = BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return LINE_COMMENT.sub("", text)


def collect_labels(text):
    """抽取文本里定义的所有 label"""
    return set(LABEL_DEF.findall(text))


def collect_refs(text):
    """抽取文本里引用的所有 &label"""
    return set(LABEL_REF.findall(text))


def upstream_dtsi_dir(dts_dir, extra_dirs):
    """在候选目录里找上游 dtsi 文件，返回 {文件名: 路径}

    ⚠ 只扫描**显式传入**的目录。
      绝不扫描板级 dts 所在目录 —— 那会把同目录下与本板无关的
      其它 dtsi（例如厂商 BSP 快照里的 rtc label）也算进来，
      导致「引用了但没定义」的 label 被误判为已定义 → 漏报。
    """
    found = {}
    for d in extra_dirs:
        if not d or not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".dtsi"):
                found.setdefault(fn, os.path.join(d, fn))
    return found


def collect_upstream_labels(board_text, dtsi_index):
    """沿 include 链收集上游定义的 label

    只解析「板级 dts 实际 include 到的」那些文件，并递归解析它们自己的
    include —— 而不是把目录里所有 dtsi 都算进来。这样上游 label 集合
    与真实编译时可见的 label 集合一致，判断才可靠。
    """
    labels = set()
    seen = set()
    queue = list(re.findall(r'^\s*#include\s+"([^"]+)"', board_text, re.M))
    while queue:
        fn = queue.pop(0)
        if fn in seen:
            continue
        seen.add(fn)
        path = dtsi_index.get(fn)
        if not path:
            continue
        try:
            t = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        t = strip_comments(t)
        labels |= collect_labels(t)
        queue.extend(re.findall(r'^\s*#include\s+"([^"]+)"', t, re.M))
    return labels, seen


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    board = sys.argv[1]
    extra = sys.argv[2:]

    if not os.path.isfile(board):
        print("找不到板级 dts: %s" % board)
        return 2

    raw = io.open(board, encoding="utf-8").read()
    # 只在 include 之前的部分找板级 label（含 root 节点内定义的 label）
    body = strip_comments(raw)

    board_labels = collect_labels(body)
    board_refs = collect_refs(body)

    # 上游 label：只沿 include 链收集
    dtsi = upstream_dtsi_dir(os.path.dirname(os.path.abspath(board)), extra)
    upstream_labels, upstream_files = collect_upstream_labels(body, dtsi)

    all_labels = board_labels | upstream_labels

    # ---- 检查 1：只 include 一份 SoC dtsi ----
    inc = re.findall(r'^\s*#include\s+"([^"]+)"', body, re.M)
    soc_inc = [i for i in inc if i.startswith("meson-g12b-") or i.startswith("meson-g12")]
    fail = 0
    if len(soc_inc) != 1:
        print("::error file=%s::应恰好 include 1 个 SoC dtsi，实际 %d 个（%s）"
              % (os.path.basename(board), len(soc_inc), " ".join(soc_inc)))
        fail = 1
    elif soc_inc[0] != SOC_DTSI:
        print("::error file=%s::本板是 A311D，应 include %s，实际 %s"
              % (os.path.basename(board), SOC_DTSI, soc_inc[0]))
        fail = 1

    # ---- 检查 2：label 名不能含 '-' ----
    # cpp 会把 label 里的 '-' 当成减号，展开成 `foo - bar: ...`，
    # dtc 先读到 'foo'，期待 ':' 却看到 '-' → 编译期语法错误：
    #     Error: xxx.dts:NNN.MM-MM syntax error
    # 节点名本身带 '-' 没问题（dtc 会重新拼接），但 label 不行。
    # 上游 147 处 gpio-hog 用例没有一个带 label，就是这个原因。
    #   (c) 2026-10-21: dt/meson-halo-a311d.dts 的 hog 节点
    #       `fusb340-sel-hog: fusb340-sel-hog {` 就是这么翻车的。
    bad_labels = []
    for line_no, line in enumerate(body.split("\n"), 1):
        # label 的合法字符集不含 '-'，所以这里要**先允许** '-' 出现在
        # 候选里，再判断它是否真的含 '-'。否则正则根本匹配不上带连字符的
        # label，检查就成了永远绿。
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*[A-Za-z_@]", line)
        if m and "-" in m.group(1):
            bad_labels.append((line_no, m.group(1), line.strip()))
    for line_no, lab, text in bad_labels:
        print("::error file=%s:%d::label `%s` 含连字符 —— cpp 会把它当减号拆开，"
              "dtc 报语法错误（节点名可以有 '-'，label 不行）"
              % (os.path.basename(board), line_no, lab))
        print("::error::   %s" % text)
        fail = 1

    # ---- 检查 3：&label 引用必须有定义 ----
    missing = sorted(board_refs - all_labels)
    if missing:
        print("::error file=%s::引用了未定义的 label：%s"
              % (os.path.basename(board), ", ".join("&" + m for m in missing)))
        print("::error::提示：删节点时必须同步改掉所有 &label 引用"
              "（例如删掉 rtc@51 节点后，aliases 里的 rtc0 = &rtc 就成了悬空引用）")
        fail = 1

    # ---- 输出信息 ----
    print("%s: 板级 label %d 个，&引用 %d 个，上游 dtsi %d 个（label %d 个）"
          % (os.path.basename(board), len(board_labels), len(board_refs),
             len(upstream_files), len(upstream_labels)))
    if missing:
        print("  悬空引用: %s" % ", ".join("&" + m for m in missing))
    else:
        print("  悬空引用: 无 ✓")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
