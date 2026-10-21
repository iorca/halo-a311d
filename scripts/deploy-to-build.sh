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
# 2. family 覆盖 —— uboot_custom_postprocess()
#
# 作用：把 halo-a311d 加进上游 meson-g12b.conf 的 VIM3 空操作分支，
#   避免落到 else 分支的 "exit 2"。
#   FIP 组装本身由 board conf 的 hook 完成（用 LibreELEC 的 khadas-vim3 目录）。
# -----------------------------------------------------------------------------
mkdir -p "$UP/config/sources/families"
install -m 0644 "$REPO_ROOT/config/sources/families/meson-g12b.conf" \
              "$UP/config/sources/families/meson-g12b.conf"
echo "✓ config/sources/families/meson-g12b.conf"

# -----------------------------------------------------------------------------
# 2. FIP —— 不再自己维护！
#
#armbian 的 fetch_sources_tools__libreelec_amlogic_fip() 会自动把
#   LibreELEC/amlogic-boot-fip clone 到 $SRC/cache/sources/amlogic-boot-fip，
#   我们在 board conf 里用 hook 指定 khadas-vim3 目录即可：
#     uboot_g12_postprocess "${SRC}"/cache/sources/amlogic-boot-fip/khadas-vim3 g12b
#
#为什么不用自己的 fip/ 目录（2026-10-19 踩过的坑）:
#   1. 仓库里的 fip 是从厂商 SDK 拷的，aml_encrypt_g12b / bl2.bin / bl30.bin /
#      bl31.img 都与 LibreELEC 不同，而 ddr*.fw 却相同 —— 混用导致
#      "FW file ddr4_1d.fw magic error!" + bootmk fail
#   2. 自己维护 = 要管 git-lfs + 文件权限位（Windows 上 git 记100644）
#   3. 用 LibreELEC 的，自动跟随上游更新

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
# 4. U-Boot 模式选择脚本（冷切换）
# -----------------------------------------------------------------------------
# ⚠⚠ 旧代码是个**假成功**（2026-10-21 查出）:
#     install ... "$BUILD_DIR/fip/halo-a311d/althaea-mode.hush" 2>/dev/null || true
#     echo "✓ althea-mode.hush"
#   - 目标目录 $BUILD_DIR/fip/halo-a311d **全仓库没有任何地方创建**
#     （grep 确认：除这行自己外无人写过该路径）→ install 每次必然失败
#   - stderr 被 2>/dev/null 吞、失败被 || true 吞
#   - 紧接着**无条件**打印 ✓ —— CI 每次都宣称部署成功，实际一个字节都没落地
#
# 正确机制（armbian lib/functions/rootfs/customize.sh:23-34）:
#   $UP/overlay            → bind-mount 成 chroot 里的 /tmp/overlay（**只读**）
#   $UP/customize-image.sh → 在 chroot 内被执行
#   ⚠ overlay **只是传文件通道，不会自动进镜像**；必须由 customize-image.sh
#     自己在 chroot 里 cp 到 /boot 才会真正落到镜像中。
MODE_SRC="$REPO_ROOT/boot/althaea-mode.hush"
MODE_OVERLAY="$UP/overlay/boot"
mkdir -p "$MODE_OVERLAY"
# ⚠ 这里刻意不写 2>/dev/null、不写 || true：失败就该当场炸出来
install -m 0644 "$MODE_SRC" "$MODE_OVERLAY/althaea-mode.hush"
# 硬校验 —— 不在成功路径上也要复核真的落地了
if [ ! -s "$MODE_OVERLAY/althaea-mode.hush" ]; then
    echo "✗ althaea-mode.hush 未部署到 $MODE_OVERLAY" >&2
    exit 1
fi
echo "✓ overlay/boot/althaea-mode.hush  ($(wc -c < "$MODE_OVERLAY/althaea-mode.hush") B)"

# chroot 内执行的定制脚本 —— 少了它，overlay 里的文件永远不会进镜像
CUSTOM_SRC="$REPO_ROOT/scripts/customize-image.sh"
if [ ! -f "$CUSTOM_SRC" ]; then
    echo "✗ 缺少 $CUSTOM_SRC —— overlay 里的文件不会进镜像" >&2
    exit 1
fi
install -m 0755 "$CUSTOM_SRC" "$UP/customize-image.sh"
if [ ! -x "$UP/customize-image.sh" ]; then
    echo "✗ customize-image.sh 未部署到 $UP" >&2
    exit 1
fi
echo "✓ customize-image.sh  (overlay -> /boot)"

# -----------------------------------------------------------------------------
# 6. 引导脚本覆盖 —— USB3.0 / PCIe 冷切换
#
#    armbian 优先取 $USERPATCHES_PATH/bootscripts/<BOOTSCRIPT 源名>，命中就用它
#    覆盖自己的那份（lib/functions/rootfs/distro-agnostic.sh:190-195）。
#    本板的 BOOTSCRIPT 源名是 **boot-meson64.cmd**，实测日志：
#      "Deploying boot script .../config/bootscripts/boot-meson64.cmd -> /boot/boot.cmd"
#    armbian-bsp-cli 的 postinst 会用 mkimage 把它编成 /boot/boot.scr。
#
#    ⚠ 只改 boot.cmd 不够：还要
#      - board conf 打开 CONFIG_CMD_GPIO（否则没有 gpio 命令）
#      - dt/meson-halo-a311d-pcie.dts 的 fusb340_hog 改成 output-high
#        （内核 gpio-hog 会覆盖 u-boot 设的电平，两边必须一致）
# -----------------------------------------------------------------------------
BOOT_SRC="$REPO_ROOT/boot/boot-meson64.cmd"
mkdir -p "$UP/bootscripts"
if [ ! -f "$BOOT_SRC" ]; then
    echo "✗ 缺少 $BOOT_SRC —— 冷切换不会生效" >&2
    exit 1
fi
install -m 0644 "$BOOT_SRC" "$UP/bootscripts/boot-meson64.cmd"
if [ ! -s "$UP/bootscripts/boot-meson64.cmd" ]; then
    echo "✗ boot-meson64.cmd 未部署到 $UP/bootscripts" >&2
    exit 1
fi
echo "✓ bootscripts/boot-meson64.cmd  (覆盖 armbian boot.cmd，含冷切换)"

echo
echo "==> 部署完成。编译命令："
echo "    cd $BUILD_DIR"
echo "    ./compile.sh kernel BOARD=halo-a311d BRANCH=current"
