#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查两条发行线是否同步。

## 为什么需要这道检查

本仓库有两条并行发行线，它们共享 95% 的内容，但**分支不同、产物不同**：

| 分支 | u-boot 来源 | Release 后缀 |
|---|---|---|
| `main` | LibreELEC khadas-vim3 FIP（含厂商原版 u-boot） | `-libreelec` |
| `gxlimg-full-mainline-uboot` | gxlimg 重打包厂商 FIP（主线 u-boot） | `-mainline` |

共享的部分（板级 DTS、CI 护栏脚本、禁用 patch、workflow）一旦只改一边，
就会**静默漂移**：CI 照样全绿，但两条线的产物行为不一致。

这不是假设 —— 2026-10-22 一天之内就因为"cherry-pick 后忘了切回分支"
把两个 commit 提交到了 gxlimg 分支，main 上没有。两条分支的
`.github/workflows/kernel.yml` 内容完全相同，所以 CI 一点异常都没报。

**人总会犯错。护栏要能在人犯错时立刻把红点亮出来，而不是靠记性。**

## 规则

1. **必须逐字节一致**（任何差异都报错）：
   - `dt/**`                    板级 DTS —— 两条线用同一份硬件描述
   - `patch/**`                 禁用 armbian OPP patch 的 0 字节文件
   - `.github/workflows/**`      CI 护栏本身
   - `scripts/**`（除 `deploy-to-build.sh`）  所有检查脚本

2. **允许差异，但必须受控**：
   - `scripts/deploy-to-build.sh`
     → gxlimg 版是 main 版的**超集**：main 的有效代码行必须作为
       **有序子序列**出现在 gxlimg 版里（注释与空行不算）。
       这样"gxlimg 删掉了 main 的某段逻辑"会被抓到，而"FIP 段新增"不会误报。
   - `config/boards/halo-a311d.conf`、`boot/boot-meson64.cmd`、`docs/**`
     → 两条线的 u-boot 来源本就不同，允许不同（只做提示）。

3. **只允许 gxlimg 有**：`fip-blob/**`（厂商 FIP blob，main 用 LibreELEC 方案不需要）。
   main 侧出现 fip-blob 同样是错（会让 main 的构建去注入不需要的 blob）。

## 用法

```bash
python3 scripts/check-branch-sync.py \
    --repo . \
    --ref-a origin/main \
    --ref-b origin/gxlimg-full-mainline-uboot
```

退出码：0 = 同步；1 = 不同步（并逐条说明原因）。
"""

import argparse
import os
import subprocess
import sys

# 必须逐字节一致的目录前缀
MUST_MATCH_DIRS = [
    "dt/",
    "patch/",
    ".github/workflows/",
]

# 允许（且必须）不同的文件 —— 有意的 u-boot 来源差异
CONTROLLED_DIFF_FILES = [
    "scripts/deploy-to-build.sh",
]

# 只做提示、不报错的差异（两条线本来就不同）
ALLOWED_DIFF_FILES = [
    "config/boards/halo-a311d.conf",
    "boot/boot-meson64.cmd",
    "README.md",
]

# 只允许 B 侧（gxlimg）存在的路径前缀
B_ONLY_PREFIXES = [
    "fip-blob/",
]

# 允许不同的目录前缀
ALLOWED_DIFF_DIRS = [
    "docs/",
]


def git(repo, *args):
    r = subprocess.run(
        ["git", "-C", repo] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return r.returncode, r.stdout, r.stderr


def git_out(repo, *args):
    rc, out, err = git(repo, *args)
    if rc != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {err.strip()[:300]}")
    return out


def list_files(repo, ref):
    """ref 下全部文件（相对路径）"""
    out = git_out(repo, "ls-tree", "-r", "--name-only", ref)
    return set(x for x in out.splitlines() if x)


def show(repo, ref, path):
    rc, out, _ = git(repo, "show", f"{ref}:{path}")
    if rc != 0:
        return None
    return out


def code_lines(text):
    """有效代码行：去掉空行与纯注释行"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def is_ordered_subsequence(small, big):
    """small 是否是 big 的有序子序列"""
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def classify(path):
    """返回 (类别, 允许吗)"""
    for p in MUST_MATCH_DIRS:
        if path.startswith(p):
            return "must-match", False
    if path.startswith("scripts/"):
        if path in CONTROLLED_DIFF_FILES:
            return "controlled", True
        return "must-match", False
    if path in ALLOWED_DIFF_FILES:
        return "allowed", True
    for p in ALLOWED_DIFF_DIRS:
        if path.startswith(p):
            return "allowed", True
    for p in B_ONLY_PREFIXES:
        if path.startswith(p):
            return "b-only", True
    return "unknown", False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref-a", default="origin/main")
    ap.add_argument("--ref-b", default="origin/gxlimg-full-mainline-uboot")
    ap.add_argument("--label-a", default="main")
    ap.add_argument("--label-b", default="gxlimg")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    A, B = args.ref_a, args.ref_b

    for ref in (A, B):
        rc, _, _ = git(repo, "rev-parse", "--verify", ref)
        if rc != 0:
            print(f"❌ 拿不到 ref {ref} —— CI 里需要先 fetch 另一个分支")
            print(f"   提示: git fetch --no-tags --depth=1 origin "
                  f"{args.label_b}:refs/remotes/origin/{args.label_b} "
                  f"{args.label_a}:refs/remotes/origin/{args.label_a}")
            return 1

    files_a = list_files(repo, A)
    files_b = list_files(repo, B)
    all_files = sorted(files_a | files_b)

    errors = []
    notes = []
    only_a = sorted(files_a - files_b)
    only_b = sorted(files_b - files_a)

    print(f"=== 两条发行线同步检查 ===")
    print(f"  A = {A}  ({len(files_a)} 个文件)")
    print(f"  B = {B}  ({len(files_b)} 个文件)")
    print()

    # ---------- 1. 必须逐字节一致 ----------
    checked = 0
    for path in all_files:
        kind, allowed = classify(path)
        if kind != "must-match":
            continue
        in_a, in_b = path in files_a, path in files_b
        if in_a != in_b:
            side = f"只在 {args.label_b}" if in_a else f"只在 {args.label_a}"
            errors.append(f"[必须一致] {path} —— {side}（这一类文件两条线必须同时存在）")
            continue
        if show(repo, A, path) != show(repo, B, path):
            errors.append(f"[必须一致] {path} —— 两条线内容不同（板级 DTS / CI 脚本 / "
                          f"workflow / 禁用 patch 必须完全相同）")
        checked += 1
    print(f"  逐字节一致性检查：{checked} 个文件")

    # ---------- 2. deploy-to-build.sh：gxlimg 必须是 main 的超集 ----------
    dep = "scripts/deploy-to-build.sh"
    if dep in files_a and dep in files_b:
        ca = code_lines(show(repo, A, dep) or "")
        cb = code_lines(show(repo, B, dep) or "")
        if not is_ordered_subsequence(ca, cb):
            missing = [l for l in ca if l not in cb]
            errors.append(
                f"[受控差异] {dep} —— {args.label_b} 版不是 {args.label_a} 版的超集："
                f"{args.label_a} 有 {len(missing)} 行有效代码在 {args.label_b} 里找不到。"
                f"（{args.label_b} 只能**增加** FIP 相关逻辑，不能删改 {args.label_a} 的逻辑）")
            for l in missing[:6]:
                errors.append(f"            丢失: {l[:100]}")
        else:
            print(f"  {dep}: {args.label_b} 是 {args.label_a} 的超集 ✅"
                  f"（{args.label_a} {len(ca)} 行有效代码全部保留）")

    # ---------- 3. 单边存在的文件 ----------
    for path in only_a:
        kind, allowed = classify(path)
        if kind == "b-only":
            errors.append(f"[只允许 {args.label_b} 有] {path} —— 出现在 {args.label_a} 侧。"
                          f"厂商 FIP blob 只属于 gxlimg 线，main 用 LibreELEC 方案，"
                          f"带上它会让 main 的构建去注入不需要的 blob")
        elif allowed:
            notes.append(f"{path} 只在 {args.label_a} 有（允许）")
        elif kind == "must-match":
            pass          # 已在第 1 步报过，不重复
        else:
            errors.append(f"[漏同步] {path} 只在 {args.label_a} 有，{args.label_b} 没有 —— "
                          f"这一类文件两条线必须同时存在")
    for path in only_b:
        kind, allowed = classify(path)
        if kind == "b-only":
            notes.append(f"{path} 只在 {args.label_b} 有（预期，允许）")
        elif allowed:
            notes.append(f"{path} 只在 {args.label_b} 有（允许）")
        elif kind == "must-match":
            pass          # 已在第 1 步报过，不重复
        else:
            errors.append(f"[漏同步] {path} 只在 {args.label_b} 有，{args.label_a} 没有 —— "
                          f"这一类文件两条线必须同时存在")

    # ---------- 4. 允许差异的文件，做个提示 ----------
    for path in sorted(files_a & files_b):
        kind, allowed = classify(path)
        if kind == "allowed" and show(repo, A, path) != show(repo, B, path):
            notes.append(f"{path} 两条线不同（允许：u-boot 来源本就不同）")

    # ---------- 输出 ----------
    if notes:
        print()
        print("提示（不报错）：")
        for n in notes:
            print(f"  · {n}")

    print()
    if errors:
        print(f"❌ 两条发行线不同步 —— {len(errors)} 处问题：")
        for e in errors:
            print(f"  {e}")
        print()
        print("  修法：把缺失的改动同步到另一条分支")
        print("  git checkout <另一条分支> && git cherry-pick <commit>")
        print("  或用本地同步脚本：scripts/sync-to-both-lines.sh")
        return 1

    print("✅ 两条发行线同步 —— 必须一致的部分逐字节相同，"
          "受控差异（deploy 脚本）方向正确")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"❌ 检查脚本自身出错: {e}", file=sys.stderr)
        sys.exit(2)
