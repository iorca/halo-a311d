#!/usr/bin/env bash
# =============================================================================
# halo-a311d —— 把本仓库内容部署进 armbian-build 的 userpatches 机制
#
# 用法（在 iorca/halo-a311d-armlan 仓库根目录执行）:
#   ./scripts/deploy-to-build.sh [ARMBIAN_BUILD_DIR]
#
# 机制依据（armbian/build 源码）:
#   config_source_board_file():  "${SRC}/config/boards" 与
#                               "${USERPATCHES_PATH}/config/boards" 都会被 source
#   source_family_config_and_arch(): core 的 family conf 先 source，
#                               本仓库的同名文件后 source（同一 shell）
#                               → 函数重定义生效，无需改上游
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${1:-${ARMBIAN_BUILD_DIR:-$HOME/armbian-build}}"

[ -d "$BUILD_DIR/userpatches" ] || {
    echo "✗ 不是 armbian-build 目录: $BUILD_DIR" >&2
    echo "  用法: $0 /path/to/armbian-build" >&2
    exit 1
}

UP="$BUILD_DIR/userpatches"

echo "==> 仓库:   $REPO_ROOT"
echo "==> 目标:   $BUILD_DIR"

# -----------------------------------------------------------------------------
# 1. 板级配置
# -----------------------------------------------------------------------------
mkdir -p "$UP/config/boards"
install -m 0644 "$REPO_ROOT/config/boards/halo-a311d.conf" \
              "$UP/config/boards/halo-a311d.conf"
echo "✓ config/boards/halo-a311d.conf"

# -----------------------------------------------------------------------------
# 2. family 覆盖（u-boot FIP 组装）
# -----------------------------------------------------------------------------
mkdir -p "$UP/config/sources/families"
install -m 0644 "$REPO_ROOT/config/sources/families/meson-g12b.conf" \
              "$UP/config/sources/families/meson-g12b.conf"
echo "✓ config/sources/families/meson-g12b.conf"

# -----------------------------------------------------------------------------
# 3. FIP 树 —— 必须放 cache/ 之外！
#    fetch_sources_tools__libreelec_amlogic_fip() 会把 LibreELEC 的
#    amlogic-boot-fip clone 到 $SRC/cache/sources/ 并 git clean 掉未跟踪内容。
#    LibreELEC 没有 halo-a311d 目录 → 拷进 cache 每次构建都被删。
#    症状: uboot_g12_postprocess 报 blx_fix.sh: No such file (127)
# -----------------------------------------------------------------------------
mkdir -p "$BUILD_DIR/fip/halo-a311d"
cp -a "$REPO_ROOT/fip/halo-a311d/." "$BUILD_DIR/fip/halo-a311d/"
echo "✓ fip/halo-a311d ($(ls -1 "$BUILD_DIR/fip/halo-a311d" | wc -l) 个文件)"

# -----------------------------------------------------------------------------
# 4. 内核 dts —— 目录名随内核大版本变，必须动态派生，不能写死
#    BRANCH 决定目录： current → meson64-current
#                       edge   → meson64-edge (上游路径可能不同)
#    写死 = 「镜像编出来了但里面没有本板 dtb」那个坑
# -----------------------------------------------------------------------------
# ⚠⚠ 目录名必须与 armbian 的 KERNELPATCHDIR 严格一致，否则 dts 不会进内核。
#
# 上游依据 config/sources/common.conf:126-128:
#     KERNELPATCHDIR="archive/${KERNEL_PATCH_ARCHIVE_BASE}-${KERNEL_MAJOR_MINOR}"
#   而 config/sources/families/include/meson64_common.inc 的 case $BRANCH:
#     current → 6.12/6.18  → KERNEL_MAJOR_MINOR=6.18
#     edge   → 7.3
#     oldlts → 6.12
#   KERNEL_PATCH_ARCHIVE_BASE = meson64（来自 LINUXFAMILY）
#
# 所以 BRANCH=current 必须是 **archive/meson64-6.18**，
#    写成 meson64-current 会让板级 dts被静默忽略
#    （症状：编译成功、deb 产出，但 linux-dtb 里没有本板 dtb）。
BRANCH_NAME="${HALO_KERNEL_BRANCH:-current}"
case "$BRANCH_NAME" in
    current)      KMM="6.18" ;;
    edge)         KMM="7.3"  ;;
    bleedingedge) KMM="7.4"  ;;
    oldlts)       KMM="6.12" ;;
    *)            KMM="6.18" ;;
esac

DT_DIR="$UP/kernel/archive/meson64-${KMM}/dt"
mkdir -p "$DT_DIR"
install -m 0644 "$REPO_ROOT/dt/meson-halo-a311d.dts"      "$DT_DIR/"
install -m 0644 "$REPO_ROOT/dt/meson-halo-a311d-pcie.dts" "$DT_DIR/"
echo "✓ $DT_DIR  (BRANCH=$BRANCH_NAME → KERNEL_MAJOR_MINOR=$KMM)"

# -----------------------------------------------------------------------------
# 5. U-Boot 模式选择脚本（冷切换）
# -----------------------------------------------------------------------------
install -m 0644 "$REPO_ROOT/boot/althaea-mode.hush" \
              "$BUILD_DIR/fip/halo-a311d/althaea-mode.hush" 2>/dev/null || true
echo "✓ althea-mode.hush"

echo
echo "==> 部署完成。编译命令："
echo "    cd $BUILD_DIR"
echo "    ./compile.sh kernel BOARD=halo-a311d BRANCH=current"
