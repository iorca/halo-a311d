# 本板 FIP blob（gxlimg 全主线方案用）

## 这个目录放什么

**一个完整的厂商 FIP 文件**，二选一：

| 文件名形态 | 大小参考 | 来源 |
|---|---|---|
| `DDR.USB` | ~1.5 MB | 厂商 USB 线刷包解包 |
| `mmcblk1boot0` | 4 MB | 设备 eMMC boot area 的 dd |
| `fip.bin` / `FIP.img` | 1~4 MB | 厂商 SDK / 其他来源 |

## ⚠ 必须是「未解包的整体文件」

gxlimg 的工作流（`extensions/gxlimg.sh:81` g12a|g12b 分支）：

```
gxlimg -e <blob>            # 解包 → bl2.sign / bl30.enc / bl31.enc / ddr*.fw
rm bl33.enc                 # 删原厂 u-boot
gxlimg -t bl3x -s raw-u-boot.bin   # 主线 u-boot 重新签名成 bl33.enc
gxlimg -t fip --bl2 ... --rev v3 u-boot.bin   # 重打包
```

**必须是整体 blob，不能是 `amlogic-boot-fip` 那种解包后的散件目录。**
散件里的 `bl2.bin` 是**未签名态**，缺原厂 `bl2.sign`，重打包出来无法启动。

## 怎么拿到

### 方式 A：从厂商 USB 线刷包解包（推荐，无需拆机）

```bash
# aml_image_v2_packer 见厂商 SDK / retro98boy/amlogic-devices
aml_image_v2_packer -d <线刷包>.img burn-img-extract
# → burn-img-extract/DDR.USB 就是要放的文件
```

### 方式 B：从设备 eMMC 直接 dd（需 root）

```bash
# boot area（A311D 优先找这里）
dd if=/dev/mmcblk1boot0 of=somewhere/fip.bin bs=512 skip=1

# user area（找不到 boot area 时回退到这里，通常内容相同）
dd if=/dev/mmcblk1    of=somewhere/fip.bin bs=512 skip=1 count=8192
```

A311D 无 SD 卡槽，FIP 必须在 eMMC。

### 校验放对了

```bash
./scripts/check-fip-blob.sh
```

## 已知问题

`gxlimg` 当前版本处理 `bl3x` 时有 bug（`hashsz` 对齐 / 越界访问），
需打 amlsblk 的补丁：

- `amlsblk: Don't assume hashsz is aligned to file block`
- 或 `fix array out-of-bounds access in bl3x signature code`

二选一即可。见 retro98boy/amlogic-devices 的 cainiao-cniot-core README。

## 提交注意

单个文件 1.5~4 MB，**已配 git-lfs**（`.gitattributes` 里 `fip-blob/**`）。
