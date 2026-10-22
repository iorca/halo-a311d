#!/usr/bin/env python3
"""
校验「禁用 armbian CPU OPP 追加 patch」这件事**真的还在生效**。

背景
----
armbian/build 的 ``patch/kernel/archive/meson64-*/`` 下有
``board-odroidn2plus-Add-missing-CPU-opp.patch``，它给上游
``arch/arm64/boot/dts/amlogic/meson-g12b-a311d.dtsi`` **追加 4 个高频 OPP 档**：

    opp-table-0: + 1.908GHz(1030mV)  + 2.016GHz(1040mV)
    opp-table-1: + 2.304GHz(1030mV)  + 2.4GHz(1040mV)

它落在 patch 目录的**根层（common）**，而 armbian 的
``lib/tools/patching.py:106 find_files_patch_files()`` 会把该目录下
**所有** .patch 收进来 → 对**所有** meson64 板无条件生效，与 BOARD 无关。
（实测：同一 deb 里的 khadas-vim3.dtb 也是 9/13 档。）

这 4 档是为 **ODROID-N2+（S922X）** 加的。本板两个 regulator 的
``regulator-max-microvolt = <1050000>``（1050 mV），顶档 1040 mV
→ **电压余量仅 10 mV**（上游原表顶档 1011 mV，余量 39 mV）。
→ 决定：**不要**这 4 档，回到上游原生的 7 / 11 档。

实现方式（armbian 的机制，lib/tools/patching.py:183-187）
------------------------------------------------------------
    # An empty patch file disables the same-named patch
    # from a lower priority directory.
    for one_patch_file in NORMAL_PATCH_FILES:
        if os.path.getsize(one_patch_file.full_file_path()) == 0:
            log.info(f"Skipping empty patch file '...'")
    NORMAL_PATCH_FILES = [f for f in NORMAL_PATCH_FILES if os.path.getsize(f.full_file_path()) > 0]

且同名文件是**按文件名（不含目录）**去重的
（patching.py:172-174 ``ALL_DIR_PATCH_FILES_BY_NAME[file_name] = ...``，
user 层目录排在 core 层之后 → user 层同名文件覆盖 core 层那份）。

→ 在 user 层放一个**0 字节**的同名文件即可禁用，无需写反向 patch。

⚠⚠⚠ 这里有一个**极易静默失效**的地方
----------------------------------------
"同名"是**按文件名**匹配的，不是按内容，也不是按目录：

  * 上游把 patch **改名** → 我们的 0 字节文件不再同名 → 禁用失效
    → 产物的 OPP 表悄悄多出 4 档 → 而 dtb-check **抓不到**
    （dtb-check 编译的是「板级 DTS + 未打 patch 的上游 dtsi」，
      永远只有 7/11 档；armbian 的 patch 只存在于 armbian 的内核树里）。
  * 上游**新增**一个同样改 OPP 表的 patch（不同名）→ 同上，静默失效。
  * 我们的 0 字节文件被**误填了内容** → 它会被当成真 patch 应用
    → armbian 的 patch 反而**生效** → 同样多出 4 档。

本脚本就是守这三条。

检查什么
--------
对每个上游 ``meson64-*/`` 目录里的 **.patch** 文件：

  1. 若它**修改了 meson-g12b-a311d.dtsi 且改动涉及 OPP 表**
     （diff 里有新增/删除的 ``opp-hz`` / ``opp-microvolt`` 行）
     → 我们仓库必须有一份**同名**的 **0 字节**文件放在对应的
     ``meson64-*/`` 目录下，用来禁用它。
  2. 我们仓库里的每个 ``meson64-*/*.patch`` 都必须是 **0 字节**
     （非 0 字节 = 会被当成真 patch 应用）。
  3. 上游有、我们没有的 ``meson64-*`` 目录 / 目录里我们缺的 OPP patch
     → 报出来。

只用 ``.patch`` 文件：armbian 的 patching 只收 ``*.patch``
（``dt/`` 子目录里的 .dts 是板级 dts 覆盖，不是 patch）。

用法
----
    check-opp-patch-disable.py --armbian-dir DIR --ours-dir DIR

    DIR 形如 ``patch/kernel/archive``（里面是 meson64-6.12/ 等目录）

退出码
------
    0  禁用机制完好
    1  有问题（打印了具体原因）
    2  用法错误 / 目录不存在
"""

import argparse
import os
import re
import sys


# 上游 a311d 的 SoC dtsi（改 OPP 表就是改这个文件）
A311D_DTSI = "arch/arm64/boot/dts/amlogic/meson-g12b-a311d.dtsi"

# diff 里新增/删除行中与 OPP 表有关的属性
OPP_PROP_RE = re.compile(r"^\s*opp-(hz|microvolt|clock-latency-ns)\b")

# diff 头里的文件路径
DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.*)$")


def is_opp_patch(text):
    """这个 patch 是否改了 a311d.dtsi 的 OPP 表？

    判据：diff 里出现 a311d.dtsi，且该文件的新增/删除行里有 OPP 属性。
    只看「改了 a311d.dtsi」是不够的 —— 将来上游可能加一个只改
    a311d.dtsi 里别的东西的 patch（比如加个 regulator），
    那种 patch 不该被禁用。
    """
    if A311D_DTSI not in text:
        return False

    in_target = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            in_target = A311D_DTSI in line
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if not in_target:
            continue
        if line.startswith("+") or line.startswith("-"):
            if OPP_PROP_RE.match(line[1:]):
                return True
    return False


def list_patch_files(root):
    """root 下所有 meson64-*/ 目录里的 .patch 文件 → {meson64-xxx: [文件名]}"""
    out = {}
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        if not d.startswith("meson64-"):
            continue
        sub = os.path.join(root, d)
        if not os.path.isdir(sub):
            continue
        names = sorted(
            n for n in os.listdir(sub)
            if n.endswith(".patch") and os.path.isfile(os.path.join(sub, n))
        )
        if names:
            out[d] = names
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--armbian-dir", required=True,
                    help="armbian/build 的 patch/kernel/archive 目录")
    ap.add_argument("--ours-dir", required=True,
                    help="本仓库的 patch/kernel/archive 目录")
    args = ap.parse_args(argv)

    arm_dir, our_dir = args.armbian_dir, args.ours_dir
    if not os.path.isdir(arm_dir):
        print(f"::error::找不到 armbian patch 目录: {arm_dir}")
        return 2
    if not os.path.isdir(our_dir):
        print(f"::error::找不到本仓库 patch 目录: {our_dir}")
        return 2

    arm = list_patch_files(arm_dir)
    ours = list_patch_files(our_dir)
    if not arm:
        print(f"::error::{arm_dir} 下没有 meson64-* 目录里的 .patch —— "
              "上游结构变了？禁用 patch 的位置也要跟着改")
        return 2

    errors = []
    notes = []

    # ---- 1. 上游改 OPP 表的 patch，我们必须有一份同名 0 字节文件禁用它 ----
    for d, names in arm.items():
        our_names = set(ours.get(d, []))
        for name in names:
            path = os.path.join(arm_dir, d, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                print(f"::error::读不了 {path}: {e}")
                return 2
            if not is_opp_patch(text):
                continue
            if name not in our_names:
                errors.append(
                    f"上游 {d}/{name} 改了 {A311D_DTSI} 的 OPP 表，"
                    f"但我们没有同名的 0 字节禁用文件 → "
                    f"该 patch 仍会生效，产物的 OPP 表会多出高频档")
                continue
            our_path = os.path.join(our_dir, d, name)
            size = os.path.getsize(our_path)
            if size != 0:
                errors.append(
                    f"我们的 {d}/{name} 是 {size} 字节，不是 0 字节 → "
                    f"它会被当成真 patch 应用，禁用失效")

    # ---- 2. 我们自己的每个禁用文件都必须是 0 字节 ----
    for d, names in ours.items():
        for name in names:
            our_path = os.path.join(our_dir, d, name)
            size = os.path.getsize(our_path)
            if size != 0:
                errors.append(
                    f"我们的 {d}/{name} 是 {size} 字节，不是 0 字节 → "
                    f"禁用文件被误填了内容")
            elif d not in arm:
                notes.append(
                    f"我们的 {d}/{name} 暂时没有上游对应（上游还没有 {d} 目录）"
                    "—— 属预期（提前备着），但上游一旦加了这个目录要复查")

    # ---- 3. 上游有 OPP patch、但我们整个目录都没有 ----
    for d in arm:
        if d not in ours:
            notes.append(f"我们没有 {d}/ 目录 —— 若上游在该目录也改 OPP 表，会漏禁")

    for n in notes:
        print(f"::notice::{n}")
    if errors:
        for e in errors:
            print(f"::error::{e}")
        print()
        print("::error::armbian 的 CPU OPP 追加 patch 禁用机制已失效或不可靠。")
        print("::error::不修的话，产物的 OPP 表会多出 4 个高频档"
              "（顶档 2.4GHz/1040mV，regulator 上限只有 1050mV → 余量 10mV）。")
        return 1

    print("OK  armbian 的 CPU OPP 追加 patch 已被 0 字节同名文件禁用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
