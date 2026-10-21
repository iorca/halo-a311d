#!/usr/bin/env python3
"""
校验两个板级变体的 DTS 之间只存在「预期内」的差异。

背景
----
本仓库有两个板级变体：

    dt/meson-halo-a311d.dts        USB3.0 变体（&usb okay / &pcie disabled）
    dt/meson-halo-a311d-pcie.dts   PCIe  变体（&pcie okay / &usb disabled）

它们应当是**同一份板级描述**，只差 FUSB340 那侧的选择：
PHY（usb3_pcie_phy）归谁、PCIe 控制器是否使能、M.2 的 PERST# 用哪个脚。

这个不变式值得守住，理由有三：

  1. **两个文件是手工维护的复制品**（历史上由 work/mk_pcie_variant.py 生成，
     该脚本已删除）。任何一边单独改动而忘了另一边，两变体就会悄悄漂移。
  2. 漂移的后果很隐蔽：可能只改了一边的 LED / hog / pinctrl，
     表现为「USB3.0 模式正常，PCIe 模式某个外设不工作」——
     而两个变体是**分别发布**的，不会同时出现在一个系统里，
     所以没人会拿它们互相比较。
  3. 变体间**不应该**出现的东西（多一个 hog、少一个 pinctrl 组、
     两边属性名写法不一致）正是本仓库已经踩过的那几类坑
     （default-trigger vs linux,default-trigger、hog 位置、
      状态属性写法），靠人眼 review 两份 800 行文件极易漏。

校验方式
--------
去掉注释后逐行比较，只允许出现白名单里的差异。白名单按「差异的语义」
而不是「行号」组织，因为行号会随文件改动漂移。

用法
----
    check-variant-diff.py <变体A.dts> <变体B.dts>

退出码
------
    0  差异都在白名单内
    1  出现白名单外的差异（打印出来）
    2  用法错误 / 文件缺失
"""

import difflib
import io
import re
import sys

# 允许的差异。每条 = (正则, 说明)
# 匹配的是「归一化后的差异行」（去掉缩进、保留内容）。
ALLOWED = [
    (r'^model\s*=\s*".*";$',
     "model 字符串（两个变体本来就要区分）"),
    (r'^status\s*=\s*"(okay|disabled)";$',
     "节点 status（&usb / &pcie 互斥使能，是变体的核心差异）"),
    (r'^reset-gpios\s*=\s*<.*>;$',
     "&pcie 的 reset-gpios（PCIe 变体多一行 M.2 PERST#）"),
]

# 归一化：去空白、折叠引号内外的多余空格
def norm(line):
    s = line.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def strip_comments(text):
    """去块注释与行注释，但保留行数（便于定位）"""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text,
                  flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def code_lines(path):
    """返回 (归一化后的有效代码行列表, 原始行号列表)"""
    with io.open(path, encoding="utf-8") as fh:
        raw = fh.read()
    body = strip_comments(raw)
    lines, nums = [], []
    for i, line in enumerate(body.split("\n"), 1):
        s = norm(line)
        if not s:
            continue
        lines.append(s)
        nums.append(i)
    return lines, nums


def is_allowed(text):
    for pat, _desc in ALLOWED:
        if re.match(pat, text):
            return True
    return False


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    a_path, b_path = argv[1], argv[2]
    for p in (a_path, b_path):
        try:
            io.open(p, encoding="utf-8").read()
        except OSError as e:
            print("读不了 %s: %s" % (p, e))
            return 2

    a, a_nums = code_lines(a_path)
    b, b_nums = code_lines(b_path)

    diff = list(difflib.unified_diff(a, b, fromfile=a_path, tofile=b_path,
                                     lineterm="", n=0))
    changed = [l for l in diff
               if (l.startswith("+") or l.startswith("-"))
               and not l.startswith("+++") and not l.startswith("---")]

    if not changed:
        print("两个变体的有效代码完全相同 —— 这通常意味着有人复制时漏了改动")
        return 1

    bad = [l for l in changed if not is_allowed(l[1:])]

    print("变体差异检查：%s vs %s" % (a_path, b_path))
    print("  有效代码差异 %d 行，其中白名单外 %d 行" % (len(changed), len(bad)))
    for l in changed:
        mark = "✓" if is_allowed(l[1:]) else "✗"
        print("    %s %s" % (mark, l))

    if bad:
        print("")
        print("发现白名单外的差异 %d 处 —— 两个变体应当只差 FUSB340 那侧的选择：" % len(bad))
        print("  · model 字符串")
        print("  · &usb / &pcie 的 status")
        print("  · &pcie 的 reset-gpios")
        print("")
        print("出现别的差异通常意味着：一边改了而另一边忘了改，")
        print("或某处属性名/位置两个变体写法不一致（历史上踩过这类坑）。")
        return 1

    print("  ✓ 差异都在白名单内")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
