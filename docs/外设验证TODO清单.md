# 外设验证 TODO 清单

> 生成：2026-11-10 · 数据源：`netlist-dump/nl_parsed_full.json`（495 元件 / 393 网络）、
> `nl_values.json`、`nl_verify.net`、`dt/meson-halo-a311d.dts`、
> `docs/DTS适配要求.md`、USB 真机回读日志。
> 范围：主人指定的 5 项未验证外设。**USB 部分已搁置**，本清单只记录现状与卡点，不安排动作。
> 2026-11-10 补充：已通过 **COM22 串口（root/root，115200 8N1）真机扫描 I2C**，
> 第 1 项温湿度传感器验证通过，清单中相关结论已按真机结果更正。
> 2026-11-10 再补：第 4 项 **SPI 屏 ST7735S 软件侧已真机跑通**（fbtft + `/dev/fb2`，见第 4 节）；
> 第 2 项 AP6256 WiFi 按主人指令**战略放弃**（软件侧已穷尽，详见第 2 节）。
> ⚠ 网表的 `parttype` / `Value` 字段与实际 BOM 多处不符，**器件型号/阻值/I2C 地址一律以真机实测为准**，
> 网表只当连线参考。串口连板方法见第 8 节。
>
> **2026-11-12 归纳整理**：本次把 SPI 屏 `display@0` 与 BT `shutdown-gpios` 的源码改动
> 双分支提交并推送；温湿度 `sht40@44` 代码早已在库（`08ef98c`→`604d1be`→`5e493ec`），
> 本次只合并真机验证结论、不改 dts。另补 WiFi 走线时序排查（第 9 节）与
> DDR/VIM3 FIP 试稳（第 10 节）。状态表中所有「未 commit / 未 push」已按本次提交更正。

---

## 0. 总览

| # | 外设 | 网表位号 | DTS 现状 | 已验证 | 优先级 | 阻塞项 |
|---|---|---|---|---|---|---|
| 1 | 温湿度传感器 | U42 = SHT40（**实贴 0x44**）；U45 I2C 悬空 | `&i2c3` + `sht40@44` | ✅ **PASS** | 完成 | — |
| 2 | SDIO 网卡 AP6256 | U40 | `&sd_emmc_a` + `wifi@1` + pwrseq | ❌ | P1 | 真机 `mmc2: error -84`；**BT 已修并 PASS**；走线时序已排除（第 9 节） |
| 3 | M.2 | U29 = APCI0107-P001A | USB3 变体 `&pcie disabled` | ❌ | P1 | 必须先冷切换到 `-pcie.dtb` |
| 4 | SPI 屏 ST7735S | FPC5 (8P) | `&spicc1` + `display@0` (`sitronix,st7735r`) | ✅ **PASS（软件侧）** | 完成 | 源码已双分支提交；仅剩目视确认 |
| 5 | USB3.0 Hub | U31 = SL6341D | 无需节点（标准 hub） | ⚠ 部分 | **搁置** | VBUSVALID 被核心板挡住，测不了 |

**通用准备**（每项都要）
```bash
# 镜像：build-20261110-c25f9263（已含 dr_mode=host / SEL=66 修复）
cat /proc/device-tree/model                 # 确认板级 dtb
dmesg -T | grep -iE 'error|fail|warn' | head -50
# 串口：开机日志 althea: SEL(gpio 66 = GPIOA_2) = x / althea: fdtfile=...
```

---

## 1. 温湿度传感器 —— ✅ 已验证通过（2026-11-10 真机，COM22）

### 扫描结果
板上**没有 `i2cdetect` / `i2cget`**（i2c-tools 未装），但有 `/dev/i2c-0/1/2` 和 `python3`。
改用 `I2C_SLAVE`(0x0703) ioctl + read-byte 探测（`UU` = 地址已被内核驱动占用，
等价 i2cdetect 的 UU）：

| 总线 | name | 探测结果 |
|---|---|---|
| i2c-0 | Meson I2C adapter | 无设备应答 |
| **i2c-1** | Meson I2C adapter | **`UU:44`** — sht4x 驱动已绑定 |
| i2c-2 | DesignWare HDMI | **0x30** 应答（HDMI EDID/PHY，非本项） |

### 驱动与实时读数（PASS）
```
/sys/bus/i2c/devices/1-0044/driver -> ../../../../bus/i2c/drivers/sht4x
/sys/class/hwmon/hwmon3/name = sht4x
temp1_input     = 31367   → 31.367 °C
humidity1_input = 25406   → 25.406 %RH
```
`zcat /proc/config.gz` 确认 `CONFIG_SENSORS_SHT4x=m`（模块已加载并绑定）。
**结论：硬件、I2C 地址、dts 节点、驱动、hwmon 全链路正常，此项关闭，无需任何改动。**

> **代码状态（2026-11-12）**：`sht40@44` 节点早已在库（`08ef98c` 引入 →
> `604d1be` 删除 I2C 悬空的 U45 → `5e493ec` 同步两分支）。本次合并**只带验证结论文档**，
> dts 一行未改。`reg = <0x44>` 不要动。

### ⚠ 更正：此前「I2C 地址写错」的判断是错的
本清单初版依据网表 `parttype = SHT40-CD1B-R3`（Sensirion datasheet Table 12：
CD1B = **0x46**）推断「dts 写 `sht40@44` 永远 probe 不上」，并建议改成 0x46。
**真机证据否决了这个推断**：0x44 上有设备、驱动绑定成功、能读出温湿度。
→ 板上实贴是 **0x44 的型号（AD1B 一类）**，网表里的 `CD1B-R3` 又是错的料号。
→ **`sht40@44` / `reg = <0x44>` 不要改。别动 dts。**
→ 已多次出现网表 `parttype` / `Value` 与实际 BOM 不符（R16/R18、R95、R94…），
   凡涉及器件型号/阻值/I2C 地址，一律以真机实测为准，网表只当连线参考。

### 网表连线（仅作参考，型号不可信）
| 器件 | bom | 供电 | I2C |
|---|---|---|---|
| **U42** | yes | pin3 = A_3V3，pin4/5 = GND | pin1 `TOUCH_I2C_SDA` → CN2.62 (GPIOA_14) + FPC3.17；pin2 `TOUCH_I2C_SCL` → CN2.64 (GPIOA_15) + FPC3.18 → **落在 i2c-1** |
| **U45** | yes | pin3 = **VDDIO_AO18 (1.8V)** | pin1/2 `I2C_AO_S0_SDA/SCL` **各只有 1 个连接点 = 全悬空、无上拉** → i2c-0 无设备，吻合 |

`docs/DTS适配要求.md:673`「U42/U45 两颗都贴装、分挂两个控制器、同地址 0x44 合法」——
与网表和真机都矛盾，**作废**；`:688` 与 dts 头部注释「U45 I2C 单端悬空、已移除」才是对的。

---

## 2. SDIO 网卡 AP6256（P1）

### 硬件事实（网表，U40 bom=yes）
| 功能 | U40 引脚 | 网络 → 去向 |
|---|---|---|
| SDIO D2/D3/CMD/CLK/D0/D1 | 14/15/16/17/18/19 | `WIFI_SD_*` → CN3.44/46/48/50/52/54，串阻 R138~R143，CMD 有 R144 上拉 |
| BT UART CTS/RX/TX/RTS | 41/42/43/44 | `BTUART_A_*` → CN3.74/76/78/80 |
| BT PCM DIN/CLK/DOUT/SYNC | 25/26/27/28 | `BTPCM_*` → CN3.64/66/68/70 |
| WL/控制 | 12 `GPIOX_6`→CN3.40；13 `GPIOX_7`→CN3.42；6 `GPIOX_19`→CN3.38 | dts 把 **GPIOX_6** 用作 pwrseq reset |
| BT 使能 / 唤醒 | 34 `BT_EN`→R147/R145；7 `BT_WAKE_HOST`→U39.2 | **dts 未配** |
| 32.768k 时钟 | 24 `WIFIBT_32KIN`→R148.2→CN3.62→**GPIOX_16(pwm_e)** | dts `wifi32k`(`pwm-clock`) + `&pwm_ef`/`pwm_e_pins`，真机已 enable ✅ |
| 电源 | 21 `VIN_LDO_OUT`→L11.1；22/23 相关 LDO 网络 | 需实量 |

### DTS 现状（`dt/meson-halo-a311d.dts:779-805`）
`&sd_emmc_a` okay、`bus-width=<4>`、`max-frequency=<100000000>`、`non-removable`、
`keep-power-in-suspend`、`mmc-pwrseq=<&sdio_pwrseq>`（reset = GPIOX_6，ACTIVE_LOW）、
`vmmc-supply=<&vsys_3v3>` / `vqmmc-supply=<&vddao_1v8>`、子节点 `brcmf: wifi@1 { compatible="brcm,bcm4329-fmac"; }`。

### 🔴 真机诊断结论（2026-11-10，COM22，已重扫复现）
```
mmc2: error -84 whilst initialising SDIO card
mmc2: Failed to initialize a non-removable card
/sys/bus/sdio/devices/                     → 空
/sys/kernel/debug/mmc2/err_stats          → Command CRC / Timeout / Data CRC 全 0
/sys/kernel/debug/mmc2/ios                → power mode: off, vdd: invalid, clock 0 Hz
Bluetooth: hci0: BCM: Reset failed (-110)
```
`unbind/bind ffe03000.mmc` 重扫后 `[2040.029558] mmc2: error -84` **完全复现**。
**err_stats 全 0 = CMD 线上根本没收到任何应答**，不是 CRC 错/时序问题，
而是模块没被使能或 IO 电平不匹配。已排除：dts 与 VIM3 参考逐字一致、
`meson-gx-mmc ffe03000.mmc: allocated mmc-pwrseq` 成功、`wifi32k` 32.768kHz 已 enable、
`CONFIG_BRCMFMAC=m` / `BRCMFMAC_SDIO=y`、固件齐全
（`brcmfmac43456-sdio.bin/.txt/.clm_blob`、`nvram_ap6256.txt` 都在）。

**AP6256 datasheet Pin Assignment × 网表逐脚核对**（`netlist-dump/nl_parsed_full.json`）：

| U40 脚 | datasheet | 网表实际 | 判定 |
|---|---|---|---|
| 9 VBAT | 主电源 | `$6N678` → FB1(120Ω) → **A_3V3** | ✅ |
| 12 **WL_REG_ON** | 高 = WiFi 出复位 | `GPIOX_6` → CN3.40；dts `sdio_pwrseq` 的 reset-gpios 正是 GPIOX_6（debugfs `gpio-71 ... ACTIVE LOW`，已确认被占用） | ✅ 软件正确 |
| 22 **VDDIO** | IO 电压输入 | `$6N710` → **R146 = 0Ω → VDDIO_AO18 = 1.8V**；CMD 上拉 R144=10k 也到这一域 | ⚠ 1.8V |
| 24 LPO | 32.768kHz | R148 → `WIFI_32K` → CN3.62 → **GPIOX_16 = pwm_e** | ✅ **已核实正确**：v6.18 `pinctrl-meson-g12a.c:290` `pwm_e_pins[]={GPIOX_16}`；dts `wifi32k`+`&pwm_ef/pwm_e_pins`，真机 `clk_summary` 32768Hz enable_count=1。主人 20:50 确认 32k 由核心板 GPIOX_16 提供 → 与 dts 吻合，**此项排除，不是根因** |
| 29 **SDIO_VSEL** | **`1` = VDDIO 1.8V / SDIO 3.0；`0` = VDDIO 3.3V / SDIO 2.0** | `$6N721` 只有 U40.29 + C179(1µF 到 GND) | ✅ **主人确认是官方参考电路，只用电容滤波，芯片内部有上拉。不是缺陷，别改板**（21:06 更正） |
| 34 **BT_REG_ON** | 高 = BT 出复位，**不得悬空** | `BT_EN` → R147(47k) 下拉 GND + R145(33k) → CN2-58；**dts `bluetooth` 节点没有 `shutdown-gpios`，没人拉高** | 🔴 **BT 确定死因** |

⚠⚠ **21:06 更正：上面「WiFi = SDIO_VSEL 硬件缺陷」的推断作废。**
主人确认 U40.29 只接滤波电容是**官方参考电路** → 芯片内部有上拉，默认即 1.8V/SDIO3.0 模式。
**不要加 10k 上拉、不要改板。** 上一轮「软件修不了、只能改硬件」的结论同时作废。
**WiFi 根因目前未定**，剩余候选见 `docs/AP6256_控制引脚核对清单.md` F 节；
头号缺口是 **CN3.44~54 在核心板侧是否真落在 `sd_emmc_a` 的 SDIO 脚**。

→ **BT**：BT_REG_ON 被 R147(47k) 下拉且 dts 不驱动 → `hci0: BCM: Reset failed (-110)`。
   软件可修，**本轮已改**（见下）。

**修复方案（21:06 更新）**
1. ✅ **软件（BT，已改且真机验证 PASS）**：`&uart_A` 的 `bluetooth` 节点补
   `shutdown-gpios = <&gpio GPIOA_13 GPIO_ACTIVE_HIGH>`。
   主人确认 BT_REG_ON 由 **GPIOA_13** 经 33k/47k 分压驱动（3.3×47/(33+47)≈1.94V）。
   极性依据 v6.18 `hci_bcm.c:1050/1114`。**板上用 `fdtput` 直接改 dtb + 重启验证（没编镜像）**：
   `gpio-62 (shutdown) out hi`、`hci0: BCM4345C5` + 加载 `BCM4345C5.hcd`、
   `/sys/class/bluetooth/hci0` 存在，`BCM: Reset failed (-110)` 消失。
   详见 `docs/AP6256_控制引脚核对清单.md` H 节。源码 dts 改动未 commit / 未 push。
2. 可选（不影响基本功能）：`device-wakeup-gpios = GPIOX_19`、
   `host-wakeup-gpios = GPIOA_5`（后者需先确认 1N5819 二极管极性）。
3. **WiFi**：先确认 CN3.44~54 的核心板侧映射；在此之前不改 dts、不改板。
   兜底可试 `post-power-on-delay-ms=<50>` / `max-frequency` 100M→25/50M（不保证）。

⚠ 顺带更正 `docs/DTS适配要求.md:546-549` 的 AP6256 引脚表：
`.6` datasheet 是 **BT_WAKE**（不是「WiFi/BT 电源/总使能」）、
`.13` 是 **WL_HOST_WAKE**（WLAN→HOST 输出，不是「BT 控制」）。
`.12 = WL_REG_ON` 那条才是对的。

### 验证步骤
```bash
dmesg -T | grep -iE 'mmc2|sdio|brcmf|pwrseq|mmc-pwrseq'
ls /sys/bus/sdio/devices/                 # PASS：出现 0:0001:1 / 0:0001:2 之类
ip link show                              # PASS：wlan0 存在
ls /lib/firmware/brcm/ | grep -i 4345    # PASS：brcmfmac43456-sdio.* + nvram + clm_blob
rfkill list                               # 确认没被 soft/hard block
```
**FAIL 时的排查顺序（别乱试寄存器）**
1. `error -84` 仍在 → 先量 U40 的 `VIN_LDO_OUT` / 1.8V 域是否真起来，再量 `GPIOX_6`(pwrseq reset) 是否被正确拉高释放；
2. `mmc2` 能枚举但无 wlan0 → 查 `brcmfmac` 固件/NVRAM 路径与 `brcm,bcm4329-fmac` 是否匹配 43456；
3. 供电与复位都正常仍超时 → 核对 `vqmmc-supply=<&vddao_1v8>` 与实际 IO 电压、`max-frequency=100MHz` 可先降速试。

### 独立子项：蓝牙 —— ✅ 已修复并真机 PASS（2026-11-10）
> ⚠ 本节初版写「DTS 里没有 bluetooth 子节点」是**错的**，与本节上文第 133–140 行矛盾，
> 2026-11-12 归纳时更正。

DTS 里 `&uart_A` 的 `bluetooth` 子节点一直存在（`compatible="brcm,bcm43438-bt"` +
`max-speed=<2000000>` + `wifi32k` LPO），缺的只是 `shutdown-gpios`：
BT_REG_ON(pin34) 经 R147(47k 下拉) + R145(33k) → CN2-58 = **GPIOA_13**，
不驱动时 BT 永远在复位 → `hci0: BCM: Reset failed (-110)`。
补 `shutdown-gpios = <&gpio GPIOA_13 GPIO_ACTIVE_HIGH>`（极性依据 v6.18
`hci_bcm.c:1050/1114`）后真机 PASS：`gpio-62 out hi`、`hci0 BCM4345C5`、
`BCM4345C5.hcd` 加载、`BCM: Reset failed (-110)` 消失。
**该改动与 SPI `display@0` 在同一对 dts 文件里，本次一并双分支提交。**

---

## 3. M.2（P1，依赖冷切换）

### 硬件事实（网表，U29 = APCI0107-P001A，M.2 M-key 4.2H，bom=yes）
| 功能 | U29 引脚 | 去向 |
|---|---|---|
| 供电 | 74/72/70/18/16/14/12/4/2 = A_3V3 | U1/U2 (NB680GD) 常开，**无使能脚** |
| CLK | 55/53 `PCIE_CLK_P/N` | CN2.43/45 |
| RX | 41/43 `PRN/PRP` | C97/C96 → U28.13/14 `PCIE_RX0P/N` |
| TX | 47/49 `PTN/PTP` | C95/C94 → U28.8/9 `PCIE_TX0N/P` |
| PERST# | 50 | R92 → CN2-30 → GPIOA_0（4.7k 上拉，低有效） |
| PEWAKE | 54 | R91 → CN2-32 → GPIOA_1（4.7k 上拉） |
| CLKREQ# | 52 | R93 → CN2-28 → GPIOC_7（4.7k **下拉**） |
| 参考地 | 77/76/1/3/... = GND | — |

⚠ U30 = FSW3410（**bom=no 未贴**）；M.2 的 PCIe 差分是经 **U28 FUSB340** 切换的，
不是经 U30。

### 阻塞前提（最常见白跑原因）
`&pcie` 与 `&usb` 共用 `usb3_pcie_phy`，**PHY 归属编译期定死**：
- 当前 `meson-halo-a311d.dtb`：`&usb okay` / `&pcie disabled` → **M.2 永远测不到**
- 必须刷 `meson-halo-a311d-pcie.dtb`（`&pcie okay` + `reset-gpios=<&gpio GPIOA_0 GPIO_ACTIVE_LOW>`，
  `&usb disabled`），且 FUSB340 SEL 需为 HIGH（贴 R87 上拉）或用 `althea_mode=pcie` 覆盖

### 验证步骤
```bash
# 串口开机日志先确认：althea: fdtfile=amlogic/meson-halo-a311d-pcie.dtb
dmesg -T | grep -iE 'pcie|meson-pcie|pci'
ls /sys/bus/pci/devices/                  # PASS：至少 1 个 0000:xx:xx.x（root port 也算）
cat /proc/bus/pci/devices                 # 无 lspci 时用这个
lsblk ; dmesg | grep -i nvme              # 插 NVMe 后 PASS：出现 nvme0n1
```
**FAIL 判据**：`meson-pcie ... PHY init failed` / `link never came up` → 查 SEL 电平与 `usb3_pcie_phy` 模式位；
`PERST#` 时序 → 量 GPIOA_0 上电后是否由低变高。

### 关联待验：冷切换本身
串口应见 `althea: SEL(gpio 66 = GPIOA_2) = x`；`x=0` → USB3 dtb，`x=1` → PCIe dtb。
两种 dtb 变体切换结果尚未真机确认，可和 M.2 一起验。

---

## 4. SPI 屏 ST7735S —— ✅ 软件侧已验证通过（2026-11-10 真机，COM22）

### 硬件事实（网表，FPC5 = 5001-FPC0520-08R1-00-B，8P，bom=yes）
| FPC5 脚 | 网络 | 去向 | 作用 |
|---|---|---|---|
| 1 | `SPI_LEDA` | R164.1 → Q15(MMBT3906 **PNP** 高边) ← GPIOH_8 | 背光阳极（**拉低导通 = 亮**） |
| 2 / 9 / 10 | GND | — | 地 |
| 3 | `GPIOA_3` | CN2.38, R124 | 屏 RST（低有效） |
| 4 | `GPIOA_4` | CN2.40, R126 | 屏 RS/DC（高=data） |
| 5 | `GPIOH_4` | CN2.10, FPC3.26 | **MOSI** |
| 6 | `GPIOH_7` | CN2.16, FPC3.29 | **SCLK** |
| 7 | A_3V3 | — | 屏供电 |
| 8 | `GPIOH_6` | CN2.14, FPC3.27 | **CS** |

**没有 MISO 脚**（裸屏只写）。上游 `pinctrl-meson-g12a.c:186-189` 与网表完全一致：
`spi1_mosi=GPIOH_4 / miso=GPIOH_5 / ss0=GPIOH_6 / clk=GPIOH_7`。
⚠ dts 头部旧注释把 CS/SCLK 写反，`docs/DTS适配要求.md:650` 同样写反，**均已作废**；
dts 头部注释本轮已改正。

### 驱动路径（不需要 spidev，也不需要自己写初始化序列）
- armbian 6.18 `CONFIG_FB_TFT_ST7735R=m`、`CONFIG_FB_TFT=m`、`CONFIG_SPI_MESON_SPICC=y`，
  板上 `/lib/modules/.../staging/fbtft/fb_st7735r.ko` 存在。
- v6.18 `drivers/staging/fbtft/` **只有 `fb_st7735r.c`，没有单独 st7735s**。
  `FBTFT_REGISTER_DRIVER(DRVNAME, "sitronix,st7735r", &display)` → DT compatible 必须是
  `sitronix,st7735r`；ST7735S 与 R 命令集兼容，共用同一份 128x160 init_sequence。
- 主线 `CONFIG_DRM_ST7735R` 在 armbian defconfig 里 **未开**，所以走 fbtft（`/dev/fbX`），
  不是 DRM `/dev/dri/cardX`。

### 已落地的 DTS 改动（两个 dtb 变体逐字节一致）
```dts
&spicc1 {
	...  /* 保持原有 pinctrl / num-cs / cs-gpios */
	display@0 {
		compatible = "sitronix,st7735r";
		reg = <0>;
		spi-max-frequency = <8000000>;
		reset-gpios = <&gpio GPIOA_3 GPIO_ACTIVE_LOW>;
		dc-gpios    = <&gpio GPIOA_4 GPIO_ACTIVE_HIGH>;
		led-gpios   = <&gpio GPIOH_8 GPIO_ACTIVE_LOW>;
		buswidth = <8>;
	};
};
```
**极性是源码定死的，别凭直觉改**（v6.18 `fbtft-core.c`）：
- `fbtft_reset():213-224` 先 `gpiod_set_value(reset,1)` 断言复位、再置 0 释放
  → 屏 RST 低有效 → `reset-gpios` 必须 **ACTIVE_LOW**；写成 HIGH 会让驱动结束后 RST 永久为低。
- `fbtft_backlight_update_status():131-143` 亮时 set logical 1；背光是 PNP 高边拉低导通
  → `led-gpios` 必须 **ACTIVE_LOW**。
- `dc` 高=data → **ACTIVE_HIGH**。
- `buswidth=<8>` **必填**，缺省 `fbtft_probe_common` 报 `buswidth is not set`。
- `spi-max-frequency` 必须写在**从设备**节点（控制器节点的 `max-frequency` 内核不读）。
  8MHz 是给 ST7735S SCLK 最小周期约 66ns 留裕量，可再往上试。

### 真机验证（本地替换 dtb，全程约 2 分钟，没有编镜像）
```bash
# 板上 dtc/fdtget/fdtput 都有；先备份
cp /boot/dtb/amlogic/meson-halo-a311d.dtb{,.bak3}
fdtput -c <dtb> /soc/bus@ffd00000/spi@15000/display@0
fdtput -t s <dtb> <node> compatible sitronix,st7735r
fdtput -t x <dtb> <node> reg 0x0
fdtput -t x <dtb> <node> spi-max-frequency 0x007a1200
fdtput -t x <dtb> <node> reset-gpios 0x2a 0x34 0x01   # GPIOA_3=52, ACTIVE_LOW
fdtput -t x <dtb> <node> dc-gpios    0x2a 0x35 0x00   # GPIOA_4=53, ACTIVE_HIGH
fdtput -t x <dtb> <node> led-gpios   0x2a 0x18 0x01   # GPIOH_8=24, ACTIVE_LOW
fdtput -t x <dtb> <node> buswidth    0x8
dtc -I dtb -O dts <dtb> -o /tmp/check.dts    # RC=0 再拷进 /boot，reboot
# 0x2a = periphs bank@40 的 gpio phandle（旁证：sdio reset-gpios=<0x2a 0x47 1>）
```

**结果（全部 PASS）**：
```
/sys/bus/spi/devices/spi0.0 出现、/dev/fb2 创建、fb_st7735r + fbtft 自动加载
graphics fb2: fb_st7735r frame buffer, 128x160, 40 KiB video memory, fps=20, spi0.0 at 8 MHz
/sys/class/backlight/fb_st7735r 注册；gpio-52 reset / gpio-53 dc / gpio-24 led 全被占用
SPI statistics: messages 63→78, bytes 82019→122990 (+40960 色条), errors=0
pinmux: GPIOH_4/5/7 = function spi1 (mosi/miso/clk), GPIOH_6 = spi1_ss0, current state default
```
写测试图案（四色横条 RGB565）：
```bash
echo <base64> | base64 -d | python3 -   # 128x160 struct.pack('<H', color) 写 /dev/fb2
```
⚠ `gpio-24 out lo ACTIVE LOW` = **物理低 = PNP 导通 = 背光已亮**。debugfs gpio 打印的是
raw 物理电平（旁证：`gpio-22 (spi0 CS0) out hi ACTIVE LOW`，CS 未选中本就是物理高）。
fbtft 的 `max_brightness=0` 导致 `echo 1 > brightness` 失败，属 staging 驱动限制，**不用管**。

### 仅剩的确认项
1. **目视**：屏是否显示红/绿/蓝/白四色横条（软件侧已无法再证明）。
   没插屏、或屏是别的分辨率/颜色序，都可能看不到预期图案。
2. 若颜色偏红蓝互换 → 加 boolean `bgr`；若方向不对 → 加 `rotate = <90>`（属性名是
   `rotate`，**不是** `rotation`，见 `fbtft_properties_read()`）。
3. 若分辨率不是 128x160 → 加 `width` / `height`。
4. 若想提帧率 → 逐步把 `spi-max-frequency` 提到 16/24MHz。

### ⚠ 手工改 dtb 的 phandle 坑（本轮抓到的自身错误）
**两个 dtb 变体的 phandle 分配不同**：main 里 `&gpio` = **0x2a**、pcie 里 `&gpio` = **0x07**
（pcie 的 0x2a 是 `spicc1-ss0` pinctrl 节点）。上一轮把 BT 的
`shutdown-gpios = 0x2a 0x3e 0` 同步到 pcie dtb 时没查 phandle，**指错了对象**；
本轮连同新加的三个 GPIO 一起改成 0x07。源码 dts 用 `&gpio` 符号，编译后各自解析，不受影响。
→ **手工 `fdtput` 加任何 GPIO 属性，phandle 必须逐个 dtb 从它自己的 `cs-gpios` 抄，
别跨变体复制**。改完一律 `dtc -I dtb -O dts` RC=0 + 回读属性确认。

### 状态（2026-11-12 更新）
源码 `dt/meson-halo-a311d.dts` / `-pcie.dts` **已双分支提交并推送**；
`check-variant-diff.py` RC=0、两变体 spicc1 段逐字节一致、括号 61/61。
同一批 dts 改动还包含 BT `shutdown-gpios`（真机 PASS，见第 2 节），
两者物理上在同一对文件里，一并提交。
板上两个 dtb 曾手工同步 `display@0`（main=0x2a、pcie=0x07）且 dtc 反编译 RC=0；
备份 `.bak3`（加节点前）都在。
⚠ **刷镜像会覆盖板上的手工改动；要让修复进发布产物必须重编镜像**
（push 触发的 `TARGET_KIND=kernel` 只出 deb，要镜像需手动 dispatch `target=build`）。

---

## 5. USB3.0 Hub —— **搁置**（只记录，不安排动作）

### 现状
- ✅ 软件侧已修完并进镜像：`dr_mode = "host"`、三条 phys 保留、`althea_sel_num = 66`。
  真机回读：`dwc3-meson-g12a: USB2 ports: 2 / USB3 ports: 1`、xHCI 双 bus
  （`2p 480M` + `1p 5000M`）、U 盘在 `1-2` 枚举成 `usb-storage`。
- ❌ U31 (SL6341D) 仍未枚举：`lsusb` 只有两个 root hub，无 `3431:6241` / `3431:6341`；
  Bus001 Port1 与 Bus002 Port1 全空，dmesg 连一次失败的枚举事件都没有 → U31 没在 D+ 拉 1.5k。

### 硬件侧已排除（别再翻）
1.1V = 1.095V（R16=7.5k 上 / R18=9.09k 下）· A_3V3 · 24MHz±20ppm+15pF ·
RREF 实贴 205Ω（规格 200Ω 1%，偏 +2.5%，**不致完全不枚举**）·
VBUSVALID 经 R96=10k 上拉 3V3 · RSTN 4.7k+100nF **实测 3.314V（复位已释放）** ·
OC 可悬空（gang 模式唯一 OC 脚）· PWREN1/3 4.7k 上拉 ·
SS 上行经 C122/C124/C116/C117 → U28 FUSB340 · USB2 上行 HSD0P/N = CN2.27/25 ↔ U31.46/47 直连。

⚠ **FUSB340 只切 SuperSpeed 差分对，切不到 USB2 上行** → SEL 方向解释不了 USB2 侧静默。
⚠ `onboard_dev.c` 的 `reset_us=10000` 是「上电稳定等待」，**不是 RSTN 最小脉宽**（曾理解错）。

### 卡点
**VBUSVALID (U31.5) 被核心板物理遮挡，完全无法测量。**
剩余两条 unverified：
1. U31.5 若属 5V 域 / 阈值 >3.3V，3.3V 上拉会被判「上行 VBUS 无效」→ 不拉 D+ → 完全静默（最吻合现象）；
2. CN2.27/25 在核心板侧是否真是 `usb2_phy0` 的 D+/D-（本机没找到 CN2 引脚表）。

**将来若恢复，一刀切验证**：量 U31.46 (HSD0P = D+) 对地直流——
≈3.0V = hub 已拉 1.5k 上拉（问题在 SoC 侧映射/走线）；0V = hub 没拉上拉（问题在 VBUSVALID/启动状态）。

---

## 6. 其它未验证项（不展开，仅登记）

以太网 PHY LED（patch 已推，需重编带 patch 内核后真机看灯）· 冷切换 66 真机确认 ·
两个 dtb 变体切换 · eMMC 当数据盘 · IR 接收 U38(GPIOAO_5) · 运行灯 LED4(GPIOAO_10) ·
风扇 PWM(GPIOAO_11 / pwm_AO_ab) · HDMI/CEC · CH224K USB-PD 受电(U6) · 音频。

已验证：从 TF 卡启动 Armbian、以太网 1Gbps（end0、crc=0、DHCP、外网通）、
USB xHCI 双 bus + USB2 大容量存储枚举、SD 卡座、
**温湿度 SHT40（i2c-1 0x44，hwmon3，31.367℃ / 25.406%RH）**、
**SPI 屏 ST7735S（fbtft `/dev/fb2`，128x160，8MHz，errors=0，软件侧）**、
**BT（hci0 BCM4345C5，`shutdown-gpios` 修复后）**。

---

## 7. 交叉依赖 / 动手前必读

1. **改 `dt/**` / `boot/**` / `scripts/**` 共用文件必须两分支同推**，且一次
   `git push <url> main:main gxlimg...:gxlimg...` 推两个 ref；分两次会被 dtb-check 的 sync 步判红。
2. `boot/boot-meson64.cmd`（`ALLOWED_DIFF_FILES`，两分支现已一致）与
   `boot/althaea-mode.hush`（**必须逐字节一致**）别只改一边。
3. 板级 dts 必须落 `userpatches/kernel/archive/meson64-6.18/dt/`（KERNELPATCHDIR），
   写错 = 编译成功但包里没本板 dtb。
4. push 触发的 `TARGET_KIND=kernel` 只出 deb；要出镜像必须手动 dispatch `target=build`。
5. M.2 与 USB3 Hub **共用 `usb3_pcie_phy`**，一次只能验一个，必须换 dtb + 重启（冷切换）。
6. 本地 Windows 无 dtc；板上 dtc/fdtget/fdtput 可验语法。别删 `work/`。

---

## 8. 串口连板方法（COM22，已跑通）

| 项 | 值 |
|---|---|
| 端口 | `COM22` = USB-Enhanced-SERIAL **CH343** |
| 参数 | 115200, 8N1, 无流控 |
| 登录 | root / root；实测**已是登录后的 shell**，发 `\r\n` 直接出 `root@halo-a311d:~# `，不用走 login |
| 本机工具 | Python `pyserial 3.5`（已装）；无 plink |

**可靠收发的三条规矩**（踩过坑）：
1. 先 `stty -echo` 关掉终端回显，否则命令回显会混进输出、marker 解析全乱；**测完必须 `stty echo` 恢复**。
2. **一次只发一条命令**，靠「连续 0.8s 无新数据」判定输出结束，别整块粘贴多行/带中文注释的命令
   （会串行、参数多余、U-Boot/静默漏执行）。
3. 要跑多行 Python 时用 base64 单行传，避免串口行编辑吞字符：
   ```
   echo <base64> | base64 -d | python3 -
   ```

**板上工具现状**：`python3` 有；**`i2cdetect` / `i2cget` / `i2cset` 都没有**（i2c-tools 未装）。
需要扫 I2C 时直接用 `/dev/i2c-N` + `fcntl.ioctl(fd, 0x0703, addr)`（I2C_SLAVE）+ `os.read(fd,1)`，
`EBUSY(16)` 记为 `UU`（已被内核驱动占用）。`/dev/i2c-0/1/2` 均存在。


---

## 9. WiFi SDIO 走线时序排查（2026-11-12）

主人问「WiFi 启动出问题，是因为时序吗？」——**不是**。用 EDA 网络长度面板
（`wifi (12)`）逐条重算总长 = 主段（SoC 侧）+ B 段（串联电阻到模块侧）：

| NET | 主段(mil) | B段(mil) | 总长(mil) | 总长(mm) | vs CLK |
|---|---|---|---|---|---|
| WIFI_SD_D2 | 2566.0 | 160.2 | **2726.2** | 69.25 | +215.8 |
| WIFI_SD_D3 | 2573.8 | 80.2 | 2654.0 | 67.41 | +143.6 |
| WIFI_SD_CMD | 2422.0 | 161.2 | 2583.2 | 65.61 | +72.8 |
| WIFI_SD_CLK | 2430.2 | 80.2 | 2510.4 | 63.76 | 0 |
| WIFI_SD_D0 | 2279.5 | 206.1 | 2485.6 | 63.13 | −24.8 |
| WIFI_SD_D1 | 2286.7 | 80.2 | 2366.9 | 60.12 | −143.5 |

- D0–D3 跨度 **359.3 mil（9.13 mm）**，FR4 取 160 ps/inch → 飞行时间差 ≈ **57 ps**；
  CLK 相对最长 DATA 差 215.8 mil ≈ 35 ps；CLK–CMD 差 ≈ 12 ps。
- 50 / 100 / 208 MHz 下全总线长度差占周期 **0.29% / 0.57% / 1.20%**，
  远在 SDIO 源同步接口 skew 容差内，**不构成时序违例**。
- `error -84` 是初始化/握手阶段的稳定失败；时序违例的典型表现是运行中偶发
  CRC/位错，两者不吻合。**走线时序排除，PCB 不需要为此改线。**
- 12 个网络全部有 B 段（`WIFI_SD_CMDB = 161.2 mil` 存在），CMD 也串了电阻，
  不存在「CMD 缺串联电阻」的问题。
- 剩余方向：示波器量 U40 的 VCC/VDDIO 与 1.8V 切换波形、SDIO_CLK 是否起振，
  或直接换 AP6256 模块验证。

---

## 10. DDR / VIM3 FIP 试稳（2026-11-11 起，2026-11-12 收束）

- 荣品原 FIP：DDR **1392 MHz**（LPDDR4 模式，VDDQ 1.1V）。颗粒
  FLXC2004G-N1（FORESEE/江波龙）LPDDR4 模式封顶 1866 MHz/3733 MT/s，
  LPDDR4X 模式 2133 MHz/4266 MT/s。
- 用 Khadas VIM3 官方 FIP（`VIM3.u-boot.sd.bin` 0.17.3）验证：该文件带
  **512 字节 SD 头**，剥掉后才是合法 gxlimg V3 FIP（TOC@`0x10010`、
  DDRfw@`0x11790`，与荣品 blob 逐偏移对齐）。
  真机：`ddr clk to 1584MHz`、`1D/2D training succeed`、
  `cs0/cs1 DataBus & AddrBus test pass`、容量 3928MB，已 boot 到 login。
- 主人已把 **VDDQ 改到 0.61V**（实测）→ 进入 LPDDR4X 模式，
  落在 spec 0.57–0.63V 内，**安全**。⚠ 切回荣品 FIP 必须把 VDDQ 调回 **1.1V**。
- **1584 MHz 是这份 FIP 锁定的唯一训练点**（标称 1608，PLL 取整后实测 1584），
  不是「没拉满」。VIM3 没有更高档位可切；要 1866 需重训 DDR 参数表
  （在加密 BL2 里，gxlimg 解出的 `lpddr4_*.fw` 只是训练算法，不决定目标频率），
  且需 VDDQ 回 1.1V，风险更高。
- `memtester 3000M 5` 已装并起跑，主人中途叫停：跑了约 10 分钟、
  Loop 1 前 7 项测试全 ok、**零 FAILURE**，但**不构成完整稳定性验证**。
- CI run `43024035782`（gxlimg 分支 `12bc4d2`，VIM3 FIP + 主线 u-boot BL33）
  已构建成功，artifact `halo-a311d-build`（645 MB）在云端，**未拉到本地**。
  本地 `build-20261111-c25f9263` 是 **main 分支正式镜像**（荣品 FIP / 1392 MHz），
  **不是** DDR 验证镜像。
- ⚠ gxlimg 分支 `fip-blob/` 当前是**临时 VIM3 FIP** 状态（`492ce29` 换 blob、
  `12bc4d2` 剥 SD 头），荣品原 blob 已改名 `.bak` 保留在目录里。

### 状态（2026-11-12 收束）
主人已叫停 memtester（跑到 Loop 1 前 7 项全 ok、零 FAILURE，但未跑完）。
**结论：1584 MHz 能训练、能启动到 login，但稳定性没有完整验证，不能当正式配置发布。**
VIM3 FIP 没有更高档位可切，1866 MHz 需重训 DDR 表 + VDDQ 回 1.1V，暂不继续。

仓库状态已整理：
- `main` 侧多余的 `fip-blob/halo-a311d/fip-vendor-mainline-uboot.bin` **已删除**
  （main 用 LibreELEC 方案，本来就不该带厂商 blob；这是 dtb-check 判红的唯一原因）。
- `gxlimg` 侧的 VIM3 FIP 试验状态**原样保留**（`vim3-fip-0.17.3.bin` +
  荣品原 blob `.bak`），主人未决定恢复前不动它。
- `check-branch-sync.py` 回到 RC=0；dtb-check 转绿。

**恢复荣品原 FIP 的方法（待主人决定后执行）**：
```bash
git mv fip-blob/halo-a311d/fip-vendor-mainline-uboot.bin.bak \
       fip-blob/halo-a311d/fip-vendor-mainline-uboot.bin
git rm fip-blob/halo-a311d/vim3-fip-0.17.3.bin
# 硬件：VDDQ 必须从 0.61V 调回 1.1V（LPDDR4 模式），否则训练会挂
# 然后两分支一次 push
```
