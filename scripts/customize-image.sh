#!/usr/bin/env bash
# =============================================================================
# halo-a311d —— 镜像定制脚本（在 chroot 内执行）
#
# 调用方（armbian 源码依据）:
#   lib/functions/rootfs/customize.sh:23-34
#     cp   "$USERPATCHES_PATH"/customize-image.sh   -> "${SDCARD}"/tmp/customize-image.sh
#     chmod +x
#     mount -o bind,ro "$USERPATCHES_PATH"/overlay  -> "${SDCARD}"/tmp/overlay
#     chroot_sdcard /tmp/customize-image.sh "$RELEASE" "$LINUXFAMILY" "$BOARD" ...
#
# ⚠⚠ 关键认知（2026-10-21 踩过）:
#   userpatches/overlay **不会自动进镜像**。它只是 bind-mount 到 chroot 里的
#   /tmp/overlay 的一个**传文件通道**（只读）。要真正落到镜像里，必须在这里
#   手动 cp 到目标路径。
#   之前 deploy-to-build.sh 直接 install 到 $BUILD_DIR/fip/halo-a311d/
#   —— 那个目录从来没人创建，install 必然失败，又被 `2>/dev/null || true`
#   吞掉，然后无条件打印 "✓ althea-mode.hush"。假成功。
#
# 参数（armbian 传入，这里用不到但保留）:
#   $1 RELEASE  $2 LINUXFAMILY  $3 BOARD  $4 BUILD_DESKTOP  $5 ARCH
#
# ⚠ chroot 里可能是极简环境：只用 mkdir/cp/chmod，别依赖 install/rsync。
# =============================================================================
set -eu

echo "==> customize-image.sh: RELEASE=${1:-?} FAMILY=${2:-?} BOARD=${3:-?}"

# ---------------------------------------------------------------------------
# 1. U-Boot 冷切换脚本 —— 放到 /boot，供 u-boot 源码/behave 读取
#    源文件由 deploy-to-build.sh 放到 userpatches/overlay/boot/ 下
# ---------------------------------------------------------------------------
if [ -d /tmp/overlay/boot ]; then
    mkdir -p /boot
    cp -a /tmp/overlay/boot/. /boot/
    echo "--- /boot 内容 ---"
    ls -la /boot/ 2>/dev/null || true

    # 硬校验：拷完必须真的在，否则让整个构建失败
    # （armbian 会因本脚本非 0 退出而中止：customize.sh:41 exit_with_error）
    # ⚠ 用 glob 而不是 $(ls)：文件名含空格时 ls 会被拆字段
    missing=0
    for src in /tmp/overlay/boot/* /tmp/overlay/boot/.[!.]*; do
        [ -e "$src" ] || continue
        b="${src##*/}"
        if [ ! -s "/boot/$b" ]; then
            echo "✗ customize-image: $b 未落到位" >&2
            missing=1
        fi
    done
    [ "$missing" = 0 ] || exit 1
    echo "✓ overlay/boot 已部署到 /boot"
else
    echo "(无 /tmp/overlay/boot —— 跳过冷切换脚本部署)"
fi
