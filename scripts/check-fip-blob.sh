#!/usr/bin/env bash
# =============================================================================
# 校验 fip-blob/halo-a311d/ 里的厂商 FIP blob 是否可用
#
# 用法: ./scripts/check-fip-blob.sh
#
# 检查项:
#   1. blob 文件是否存在、大小是否合理
#   2. 是否为真正的 FIP（gxlimg -e 能否解包出 bl2.sign / ddr*.fw）
#   3. 解出的DDR 固件是否齐全（g12b 重打包需要 9 个 ddrfw）
#
# 需要 gxlimg：armbian 会自动编译到 cache/sources/gxlimg/gxlimg
#   若本机没有，先跑一次 armbian build，或手动 clone：
#     git clone https://github.com/repk/gxlimg && cd gxlimg && make
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOB_DIR="$REPO_ROOT/fip-blob/halo-a311d"
GXIMG="${GXIMG:-}"

echo "=== 1. 查找 blob 文件 ==="
shopt -s nullglob
candidates=()
for pat in '*.USB' '*.usb' 'mmcblk*boot*' 'fip*.bin' 'FIP*.img' 'fip*.img'; do
    for f in "$BLOB_DIR"/$pat; do
        [[ -f "$f" ]] && candidates+=("$f")
    done
done
shopt -u nullglob

if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "✗ 没找到 blob。"
    echo "  目录: $BLOB_DIR"
    echo "  需要一个**完整的厂商 FIP 文件**（DDR.USB / mmcblk1boot0 / fip.bin）。"
    echo "  获取方式见同目录 README.md"
    exit 1
fi

BLOB="${candidates[0]}"
for f in "${candidates[@]}"; do
    printf "  候选: %-40s %s\n" "$(basename "$f")" "$(du -h "$f" | cut -f1)"
done
echo
echo "  使用: $BLOB  ($(stat -c%s "$BLOB") B)"

echo
echo "=== 2. 定位 gxlimg ==="
if [[ -n "$GXIMG" && -x "$GXIMG" ]]; then
    echo "  用 GXIMG 环境变量指定的: $GXIMG"
else
    for p in \
        "$HOME/armbian-build/cache/sources/gxlimg/gxlimg" \
        /usr/local/bin/gxlimg /usr/bin/gxlimg; do
        [[ -x "$p" ]] && GXIMG="$p" && break
    done
fi
if [[ -z "$GXIMG" || ! -x "$GXIMG" ]]; then
    echo "⚠ 没找到 gxlimg，跳过解包验证。"
    echo "  仅能确认: 文件存在且大小合理。"
    echo "  要完整验证请先跑一次 armbian build，或手动编译："
    echo "    git clone https://github.com/repk/gxlimg && cd gxlimg && make"
    exit 0
fi
echo "  gxlimg: $GXIMG"

echo
echo "=== 3. 解包验证 ==="
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if ! "$GXIMG" -e "$BLOB" "$TMP" 2>&1 | sed 's/^/    /'; then
    echo "✗ gxlimg -e 解包失败 —— 这可能不是有效的 FIP blob"
    exit 1
fi

echo
echo "=== 4. 解出的内容 ==="
ls -la "$TMP" | sed 's/^/    /'

missing=0
for req in bl2.sign bl30.enc bl31.enc; do
    if [[ -f "$TMP/$req" ]]; then
        printf "  ✓ %-20s %s\n" "$req" "$(stat -c%s "$TMP/$req") B"
    else
        printf "  ✗ %-20s **缺失**\n" "$req"
        missing=1
    fi
done

echo
echo "  DDR 固件（g12b 重打包需要 9 个）:"
DDR_OK=1
for fw in ddr4_1d.fw ddr4_2d.fw ddr3_1d.fw piei.fw lpddr4_1d.fw lpddr4_2d.fw \
          diag_lpddr4.fw aml_ddr.fw lpddr3_1d.fw; do
    if [[ -f "$TMP/$fw" ]]; then
        printf "    ✓ %-22s %s B\n" "$fw" "$(stat -c%s "$TMP/$fw")"
    else
        printf "    ✗ %-22s 缺失\n" "$fw"
        DDR_OK=0
    fi
done

echo
if [[ $missing -eq 0 && $DDR_OK -eq 1 ]]; then
    echo "=== ✓ blob 可用，gxlimg 能完整解包 ==="
    echo "  可以跑: gh workflow run kernel.yml -f target=build -f release=noble"
    exit 0
fi
echo "=== ✗ blob 不完整 ==="
echo "  缺 bl2.sign/bl30.enc/bl31.enc → 不是完整的厂商 FIP，或被裁剪过"
echo "  缺 ddr 固件 → 该 FIP 不含这些 DDR 初始化代码，gxlimg 重打包会失败"
exit 1
