# 本板 FIP blob（gxlimg 全主线方案用）

## ✅ 当前已有：`fip-vendor-mainline-uboot.bin`（1,522,032 B）

`md5 = 6a01004023481ea0fcde9792e7abdb5e`

**来源**：VM 上用厂商 SDK 的工具从 `pro-a311d/` 散件重新打包生成——
```bash
~/PRO-A311D/amlogic-boot-fip/pro-a311d/   # 厂商散件（自带 aml_encrypt_g12b）
cp ~/PRO-A311D/amlogic-boot-fip/g12a.inc .
./blx_fix.sh bl30.bin zero_tmp bl30_zero.bin bl301.bin bl301_zero.bin bl30_new.bin bl30
./blx_fix.sh bl2.bin  zero_tmp bl2_zero.bin  acs.bin   bl21_zero.bin bl2_new.bin  bl2
./aml_encrypt_g12b --bl30sig --input bl30_new.bin --output bl30.g12a.enc --level v3
./aml_encrypt_g12b --bl3sig  --input bl30.g12a.enc --output bl30_new.bin.enc --level v3 --type bl30
./aml_encrypt_g12b --bl3sig  --input bl31.img --output bl31.img.enc --level v3 --type bl31
./aml_encrypt_g12b --bl3sig  --input u-boot.bin --compress lz4 --output bl33.bin.enc --level v3 --type bl33
./aml_encrypt_g12b --bl2sig  --input bl2_new.bin --output bl2.n.bin.sig
./aml_encrypt_g12b --bootmk --output u-boot.bin --level v3 \
  --bl2 bl2.n.bin.sig --bl30 bl30_new.bin.enc --bl31 bl31.img.enc --bl33 bl33.bin.enc \
  --ddrfw1 ddr4_1d.fw --ddrfw2 ddr4_2d.fw --ddrfw3 ddr3_1d.fw \
  --ddrfw4 piei.fw --ddrfw5 lpddr4_1d.fw --ddrfw6 lpddr4_2d.fw \
  --ddrfw7 diag_lpddr4.fw --ddrfw8 aml_ddr.fw --ddrfw9 lpddr3_1d.fw
```

**已验证 `gxlimg -e` 能完整解包**（在 VM 上实测）：
```
bl2.sign (65536)  bl30.enc (58736)  bl31.enc (198144)
ddr3/4_1d.fw  ddr4_2d.fw  lpddr3/lpddr4_1d/2d.fw  piei.fw  aml_ddr.fw  diag_lpddr4.fw
```
→ 这正是 gxlimg 重打包需要的全部输入，**方案可行**。

> ⚠ 注意：生成时用的 bl33 是 armbian 编译出的主线 u-boot v2022.07。
> 但 gxlimg 方案会在构建时**重新替换** bl33，所以 blob 里的 bl33 是哪版不影响。

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

FIP 在 eMMC 上（A311D 的 BootROM 只从 eMMC 加载 FIP，与 SD 卡无关）。
本板有 SD 卡座（CN1），但 SD 卡是**系统启动盘**，不是 FIP 载体。

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
