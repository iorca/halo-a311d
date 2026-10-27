#!/usr/bin/env bash
# =============================================================================
# 把一个 commit 同步到两条发行线，并推送。
#
# ## 为什么需要这个脚本
#
# 本仓库有两条并行发行线：
#   main                        → u-boot 用 LibreELEC khadas-vim3 FIP
#   gxlimg-full-mainline-uboot  → u-boot 用 gxlimg 重打包厂商 FIP
#
# 两条线共享 95% 的内容（板级 DTS、CI 护栏、禁用 patch），
# 所以**绝大多数改动必须同时出现在两条分支上**。
#
# 人手同步最容易出错的地方是"只改了一条"或者"提交到了错的分支" ——
# 2026-10-22 一天之内就因此出过两次事故（cherry-pick 后忘了切回分支）。
# 而且因为两条线的 workflow 与检查脚本内容完全相同，
# 提交错分支**不会**让任何 CI 变红 → 板级 DTS 静默漂移。
#
# 本脚本把"同步"这件事变成一条命令，并且**自己核对结果**。
#
# ## 用法
#
#   # 在 main 上改完并 commit 之后：
#   ./scripts/sync-to-both-lines.sh            # 自动用 HEAD
#   ./scripts/sync-to-both-lines.sh abc1234    # 指定 commit
#
#   # 提交到了 gxlimg 上、main 还没有时，同样能用：
#   ./scripts/sync-to-both-lines.sh abc1234
#
# 脚本会：
#   1. 确认工作区干净、commit 存在
#   2. 对每条线：若该 commit 不在分支上 → cherry-pick
#   3. 推送两条线
#   4. 跑一遍同步检查（scripts/check-branch-sync.py）确认真的同步了
#   5. 打印最终状态
#
# 退出码：0 = 同步完成并通过检查；非 0 = 失败（脚本会说明停在哪一步）
# =============================================================================
set -euo pipefail

MAIN_BRANCH="main"
GX_BRANCH="gxlimg-full-mainline-uboot"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

say()  { echo "=== $* ==="; }
fail() { echo "❌ $*" >&2; exit 1; }

# ---------------------------------------------------------------- 参数
COMMIT="${1:-HEAD}"
if ! git rev-parse --verify "$COMMIT^{commit}" >/dev/null 2>&1; then
    fail "commit 不存在: $COMMIT"
fi
COMMIT_SHA="$(git rev-parse "$COMMIT^{commit}")"
COMMIT_SHORT="$(git rev-parse --short "$COMMIT_SHA")"

say "要把 commit $COMMIT_SHORT 同步到两条发行线"

# ---------------------------------------------------------------- 前置检查
if [ -n "$(git status --porcelain)" ]; then
    echo "工作区不干净，先提交或 stash：" >&2
    git status --short >&2
    fail "工作区有未提交的改动"
fi

CURRENT="$(git branch --show-current)"
case "$CURRENT" in
    "$MAIN_BRANCH"|"$GX_BRANCH") ;;
    *) fail "当前分支是 '$CURRENT'，请先切到 $MAIN_BRANCH 或 $GX_BRANCH" ;;
esac

for b in "$MAIN_BRANCH" "$GX_BRANCH"; do
    git fetch origin "$b" >/dev/null 2>&1 || true
done

# 目标 commit 至少要在本地某条分支上（否则无从同步）
if ! git branch --contains "$COMMIT_SHA" >/dev/null 2>&1; then
    fail "commit $COMMIT_SHORT 不在任何本地分支上"
fi

# ---------------------------------------------------------------- 逐条同步
for BR in "$MAIN_BRANCH" "$GX_BRANCH"; do
    say "$BR"
    git checkout "$BR" >/dev/null 2>&1

    # ⚠⚠⚠ 绝不在这里 reset --hard：那会把"本地已提交但还没推"的东西
    #   悄悄丢掉。分支切换纪律的第一条就是**不许**替用户决定丢东西。
    #
    #   分三种状态，区别对待：
    #     落后 (behind>0, ahead=0)  → 远端有本地没有的提交 → 停，要人决定
    #     分叉 (behind>0, ahead>0)  → 两边都有对方没有的提交   → 停，要人决定
    #     领先 (behind=0, ahead>0)  → 本地待推送             → 正常，继续
    read -r BEHIND AHEAD <<< "$(git rev-list --left-right --count "origin/$BR...$BR")"
    if [ "$BEHIND" -gt 0 ]; then
        echo "  $BR 与远端分叉或落后：" >&2
        echo "    local  = $(git rev-parse --short "$BR")  (领先 $AHEAD, 落后 $BEHIND)" >&2
        echo "    remote = $(git rev-parse --short "origin/$BR")" >&2
        echo "  远端有本地没有的提交 —— 本脚本不会替你 pull/rebase/reset。" >&2
        echo "  请自己决定怎么处理。" >&2
        fail "$BR 状态不一致，已停下"
    fi

    # ⚠⚠ 判定「这个 commit 的补丁是否已经在目标分支上」必须用 **patch-id**，
    #   不能用 sha —— cherry-pick 出来的 commit sha 必然不同（内容一样、sha 不同），
    #   用 sha 判定会重复 cherry-pick → 撞上 "previous cherry-pick is now empty"。
    #
    #   `git cherry <目标分支> <commit>` 的语义（实测三轮，别再猜）:
    #     · 它比较的是 **patch-id**，与 sha 无关
    #     · 输出**每行格式 = `<符号> <sha> <subject>`**（不带 -v 也这样）
    #         `+` = 该补丁**不**在目标分支上 → 需要 cherry-pick
    #         `-` = 该补丁**已**在目标分支上 → 跳过
    #     · 输出的是 head 的整个祖先链相对 upstream 的差集，不是只有被查的那一个
    #
    #   → 判据要覆盖**两种**「已在目标分支」的情况：
    #       ① 同一个 sha（本来就是那条分支的祖先）→ `git cherry` 的差集里
    #          **压根没有它**（upstream 已含该 commit）→ 必须用 is-ancestor 判
    #       ② 不同 sha 但 patch-id 相同（cherry-pick 的产物）
    #          → `git cherry` 输出里它是 `- <sha> <subject>`
    if git merge-base --is-ancestor "$COMMIT_SHA" "$BR" 2>/dev/null || \
       git cherry "$BR" "$COMMIT_SHA" 2>/dev/null | \
            awk -v s="$COMMIT_SHA" '$1 == "-" && $2 == s { found = 1 } END { exit !found }'; then
        echo "  本地已包含 $COMMIT_SHORT（按 patch-id 判定）"
    else
        echo "  cherry-pick $COMMIT_SHORT ..."
        if ! git cherry-pick "$COMMIT_SHA"; then
            echo "  cherry-pick 冲突 —— 已保留现场，处理完执行 git cherry-pick --continue" >&2
            fail "cherry-pick 失败"
        fi
    fi
done

# ---------------------------------------------------------------- 推送
# ⚠⚠ 必须**先在两条本地分支都同步完，再一起推送**。
#   边同步边推会撞上 pre-push 钩子：推第一条时另一条还没同步 →
#   钩子判定"两条线不同步" → 拒绝推送 → 死锁。
#   （2026-10-27 实测踩到：推送 hook 本身的那个 commit 时就是这个顺序。）
say "推送"
for BR in "$MAIN_BRANCH" "$GX_BRANCH"; do
    AHEAD="$(git rev-list --count "origin/$BR..$BR")"
    if [ "$AHEAD" -gt 0 ]; then
        git push origin "$BR"
        echo "  已推送 $BR（本地领先 $AHEAD 个提交）"
    else
        echo "  $BR 与远端一致，无需推送"
    fi
done

# ---------------------------------------------------------------- 核对
say "同步检查"
if ! python3 scripts/check-branch-sync.py \
        --repo "$REPO_ROOT" \
        --ref-a "origin/$MAIN_BRANCH" \
        --ref-b "origin/$GX_BRANCH"; then
    fail "同步检查没通过 —— 上面列出了具体差异"
fi

say "最终状态"
for BR in "$MAIN_BRANCH" "$GX_BRANCH"; do
    printf "  %-30s local=%s  remote=%s\n" "$BR" \
        "$(git rev-parse --short "$BR")" \
        "$(git rev-parse --short "origin/$BR")"
done
echo
echo "✅ 两条发行线已同步并推送"
