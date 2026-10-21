# MAIN_V0.3 × 厂商 DTS 差异清单

>厂商 DTS：`/home/orca/PRO-A311D/kernel/aml-4.9/arch/arm64/boot/dts/amlogic/`
> `pro-a311d.dts` → `g12b_a311d_w400_drm_buildroot.dts` + `rp-lcd-mipi-5-720-1280-v2.dtsi`
> 厂商内核：**aml-4.9（厂商分支，非 mainline）**
> 已拉到本地 `vendor_dts/`（4 个文件）

> 📄 **本文与 `与厂家DTS比对清单.md` 的分工**（两份讲同一件事，视角不同，别混）：
> - **本文（差异清单）**：站在「本板要做什么」的**决策视角** ——
>   哪些厂商节点要保留 / 替换 / 屏蔽，附理由与实施顺序。
> - **比对清单**：站在「合并时怎么逐行核对」的**执行视角** ——
>   引脚对照表、极性表、合并后的验证 checklist。
>
> 只想查「某个外设本板用哪个脚」→ 看**比对清单**；
> 想知道「为什么这么处置」→ 看**本文**。

---

## 零、先说三个结构性差异（决定整体策略）

| 项 | 厂商 aml-4.9 | mainline | 影响 |
|---|---|---|---|
| **GPIO 控制方式** | 私有节点 `rp_power` / `rp_gpio`（`gpio_num = <&gpio GPIOA_x ...>` + `gpio_function`）| 标准 `gpios`/`gpio-leds`/`gpio-keys` | **本板节点只能按厂商风格写**，不能直接用 mainline 语法 |
| **显示通路** | MIPI DSI/CSI（`rp-lcd-mipi-*.dtsi`）| — | **本板改 SPI 屏 → 该 dtsi 整个不用** |
| **按键/LED** | 私有 `gpio_keypad` / `gpioleds`（厂商 DTS 里**均已 disabled**）| 标准 `gpio-keys`/`gpio-leds` | 需确认厂商驱动能否改配置，或改用通用驱动 |

> ⚠ `rp_gpio` 的 `gpio_function`：0=输出、1=输入、2=IRQ、**3=FLASH**、4=输出控（power）
>厂商 `run_led` 用的是 `gpio_function = <3>`（FLASH），**不是普通输出**——评估时需确认是否正确。

---

## 一、必须处理的 GPIO 冲突（🔴 严重）

厂商 DTS 已占用的脚，与本板用途**直接冲突**：

| GPIO | 厂商用途 | 位置 | 本板用途 | 冲突判定 |
|---|---|---|---|---|
| **GPIOA_0** | `rp_gpio.gpioa0` 输出 | pro-a311d.dts:124 | 按键/普通 GPIO | 🔴 **需改** |
| **GPIOA_1** | `rp_power.usb_pwr` 输出控 | pro-a311d.dts:32 | 普通 GPIO | 🔴 **需改或沿用** |
| **GPIOA_3** | `rp_power.hub_rst` 输出控 | pro-a311d.dts:36 | **屏 SPI_RST** | 🔴 **严重冲突** |
| **GPIOA_4** | `rp_power.spk_on` 输出控 | pro-a311d.dts:40 | **屏 SPI_RS** | 🔴 **严重冲突** |
| **GPIOA_6** | `bt-dev.gpio_reset` | pro-a311d.dts:157 | 普通 GPIO | 🔴 **需改** |
| **GPIOA_8** | 屏 `reset-gpio` | rp-lcd:264 | — | ⚠ **MIPI 屏专用，随 dtsi 弃用** |
| **GPIOA_9** | 屏 `irq-gpio` | rp-lcd:265 | — | ⚠同上 |
| **GPIOA_10** | `rp_gpio.gpioa10` 输出 | pro-a311d.dts:74 | 普通 GPIO | 🟡 确认 |
| **GPIOA_11** | `rp_gpio.gpioa11` 输出 | pro-a311d.dts:70 | 普通 GPIO | 🟡 确认 |
| **GPIOA_12** | `rp_gpio.gpioa12` 输出 + `reset` | pro-a311d.dts:82,436 | 普通 GPIO | 🟡 确认 |
| **GPIOH_6** | `gpio-vbus-power` + **SPI `cs-gpios`** | g12b:1530,1567 | **屏 SPI_SCLK** | 🔴 **严重冲突** |
| **GPIOAO_5** | `rp_gpio.gpioao5` **输入** | pro-a311d.dts:128 | **红外接收** | ✅ **用途一致，沿用** |
| **GPIOAO_10** | `rp_power.run_led` | pro-a311d.dts:56 | **运行灯 LED4** | ✅ **一致，沿用** |
| **GPIOAO_11** | `rp_gpio.gpioao11` 输出 | pro-a311d.dts:86 | 已释放（MT9700改硬件） | 🟡 可删 |
| **GPIOX_6** | `wifi.power_on_pin` | g12b:239 | AP6256 使能 | ✅ **一致** |
| **GPIOX_7** | `wifi.interrupt_pin` + `reset-gpio` | g12b:237,1555 | AP6256 | ✅一致 |
| **GPIOX_19** | `wifi.gpio_hostwake` | g12b:230 | AP6256 | ✅ 一致 |

### 🔴 三个必须你拍板的冲突

**① GPIOA_3 / GPIOA_4 —— 厂商当 hub_rst / spk_on 用，本板要当屏 RST/RS**

- 厂商：`A_3`=hub 复位、`A_4`=喇叭开关
- 本板：`A_3`=屏 `SPI_RST`、`A_4`=屏 `SPI_RS`
- **决定**：你这个板子要不要 USB Hub？如果 **U31(SL6341D) 在用**（网表 `bom=yes`），hub 复位就得占用A_3 → **本板屏 RST 需换脚或复用**。

**② GPIOH_6 —— 厂商当 SPI CS + USB VBUS 电源**

- 本板：`GPIOH_6` = **SPI_B_SCLK**
- **决定**：SPI 屏的 SCLK 能否改到别的脚？本板 GPIOH 组还有 4/5/7 可用（但 4/5/7 已占 MOSI/MISO/CS）。

**③ SPI 总线 —— 厂商 DTS 里没有任何 `&spiN` 节点**

- grep `&spi[0-9_]` **结果为空** → 厂商没使能任何 SPI 控制器
- 本板要 SPI 点屏 → **必须新增 SPI 节点 + pinctrl**
- ⚠ 厂商 4.9 内核的 SPI 节点名与 pinmux 写法需对照 `g12b` 的 `pinctrl` 定义确认

---

## 二、按你的需求逐项处置

### 2.1 SPI 点屏（🔴 新增）

| 项 | 本板定义 | 厂商现状 | 动作 |
|---|---|---|---|
| SPI 控制器 | `&spi_B`（bank待定）| **无节点** | **新增** |
| MOSI | GPIOH_4 | — | 新增 pinctrl |
| MISO | GPIOH_5 | 有 pinctrl(1314行) 但用途不同 | 确认复用可行性 |
| SCLK | GPIOH_6 | ⚠ 被当 SPI cs + USB vbus | **冲突，见上** |
| CS | GPIOH_7 | — | 新增 |
| 屏 RST | GPIOA_3 | ⚠ 被当 hub_rst | **冲突，见上** |
| 屏 RS | GPIOA_4 | ⚠ 被当 spk_on | **冲突，见上** |
| 背光 EN | GPIOH_8（ACTIVE_LOW，PNP 高边）| 未使用 | 新增 gpio 控制 |

> ⚠ 屏型号未知（你说"小屏幕"），SPI 屏初始化序列通常在**驱动里**或厂商 SDK 的 LCD 驱动中，不在 DTS。
> DTS 只需配好 SPI 总线 + CS + RST/RS + 背光。

### 2.2 MIPI CSI/DSI（✅ 已关闭，不用动）

| 节点 | 厂商状态 |
|---|---|
| `&csi` / `&csi2` | **不存在**（grep 无结果）|
| `&dsi` | **不存在** |
| `&isp` |存在（g12b:905），仅 reserve CMA，无 CSI 节点 |
| `rp-lcd-mipi-5-720-1280-v2.dtsi` | 被 `pro-a311d.dts:7` include |

**动作**：
1. **注释掉** `pro-a311d.dts:7` 的 `#include "rp-lcd-mipi-5-720-1280-v2.dtsi"`
2. 该 dtsi 占用 GPIOA_8/A_9、GPIOA_2、GPIOH_4 —— 注释掉后这些脚自动释放
3. ⚠ **GPIOA_2 冲突**：MIPI dtsi 把 `GPIOA_2` 当 `lcd_cpu_gpio`（第53行），而本板 `GPIOA_2` = **FUSB340 SEL** → 注释 dtsi 后解决
4. `&isp` 可一并 `status = "disabled"`（摄像头未用）

### 2.3 音频（🟡 评估保留哪些）

厂商已有完整音频链路：

| 节点 | 状态 | 说明 |
|---|---|---|
| `amlogic_codec:t9015` | **okay** | T9015 内部 codec（A311D 内置）|
| `pdm_codec` / `dummy_codec` | okay | PDM / dummy |
| `audio_effect:eqdrc` | okay | 音效 EQ |
| `auge_sound` | okay | 声卡 `AML-AUGESOUND`，用 `aml_tdmb` |
| dai-link@0 | i2s，`mclk-fs=256`，master=`aml_tdmb` | ⚠ **用的是 TDM，不是 I2S** |

**本板音频硬件**（网表）：
- `AL_CH_P/N`(CN1-37/39)、`AR_CH_P/N`(CN1-41/43) → 音频通道进核心板
- `CVBS`/`AGND_CVBS`(CN1-31/33) → 视频输入
- 板上**无外部音频 codec/功放**（U1/U2 是 NB680GD 电源，U14-U27 是 ESD/RCLAMP）

**我的判断**：本板只有**模拟音频通道 + CVBS 输入**，没有外部 codec。所以：
- `t9015` + `auge_sound` **保留**（对应 CN1 的音频通道）
- `pdm_codec` / `dummy_codec` / `audio_effect` → 🟡 **评估是否需要**（纯软件效果，可关）
- ⚠ `aml_tdmb` 是 TDM 控制器（GPIOA_3/A_4复用组）→ **与 SPI 屏 RST/RS 冲突！** 见 §一①

### 2.4 以太网（🔴 新增，厂商完全没有）

**厂商 DTS 里 grep `phy-mode` / `&gmac` / `mdio` / `ethernet-phy`全部为空——以太网完全没配。**

| 项 | 本板定义 |
|---|---|
| MAC | `&gmac0`（RGMII，与 RMII 互斥，复位时由 `PRG_ETH_REG1[0]`锁定）|
| PHY | U23 = **RTL8211F**，`reg = <1>`（strap R78→A_3V3 / R79,R80→GND）|
| **phy-mode** | **`"rgmii-id"`**（PCB 等长散布仅~1ps，2ns 必须由 PHY 内部延迟线提供）|
| 复位 | `RGMII_RST#`(CN3-2) ─R50(0Ω)─→ PHY0_RSTN(U23-12)，核心板拉低即复位 |
| 驱动 | mainline `realtek.c` 会在 `rgmii-id` 下**软件强制打开 TX+RX 双延时** |

> ⚠ `rgmii-id` 依赖 `drivers/net/phy/realtek.c`。**aml-4.9 厂商内核里这个驱动可能没有 RTL8211F 的 RX 延时处理**（该功能 2019 年才进 mainline）。
> → **必须实测验证**。若厂商驱动不支持，用 `mii-tool` 手动写 PHY 寄存器 `0xd08/0x11`。

### 2.5 温湿度 SHT40（🔴 新增一路）

| 器件 | 总线 | 引脚 | 地址 | 状态 |
|---|---|---|---|---|
| **U42** | `TOUCH_I2C` | GPIOA_14(SDA) / GPIOA_15(SCL) | 0x44 | ✅ 已启用（`&i2c3`）|
| ~~**U45**~~ | `I2C_AO_S0` | AO 域 I2C | 0x44 | ❌ **未启用** |

厂商 DTS 现有 I2C：`i2c0/i2c1/i2c2/i2c3/i2c_AO`（alias 已定义），但**无 SHT40 节点**。

⚠ **U45 未启用的原因（网表证据）**：
`I2C_AO_S0_SDA` / `I2C_AO_S0_SCL` 在网表里**各只有 1 个连接点**（就是 U45 自己），
既没接 SoC 的 AO I2C 引脚，也没有上拉电阻 → 器件收不到 ACK，驱动永远探测不到。
（U45 供电 VDDIO_AO18 与去耦 C218 都正常，仅信号线悬空。）

`&i2c_AO` 控制器本身保留（AO 域 I2C 引出到 CN3-69/71），但不挂设备节点。

### 2.6 WiFi/BT（🟡 沿用，需核对）

| 项 | 厂商 | 本板 |
|---|---|---|
| `wifi` 节点 | `amlogic, aml_wifi`，`dhd_static_buf`（BCM驱动）| AP6256（BCM）|
| `power_on_pin` | GPIOX_6 | ✅ 一致 |
| `interrupt_pin` | GPIOX_7 | ✅ 一致 |
| `bt-dev` | `gpio_reset`=GPIOA_6、`gpio_hostwake`=GPIOX_19 | ⚠ GPIOA_6 冲突（见 §一）|

⚠ 厂商用 `aml_wifi`+`dhd_static_buf`（**BCM 专有驱动**），不是 mainline `brcmfmac`。AP6256 需确认厂商 BSP 里是否已带对应驱动。

### 2.7 按键（🟡 评估）

厂商 DTS：`gpio_keypad` 和 `adc_keypad` **都是 `status = "disabled"`**，且**无 `gpio_keys` 节点**。

本板按键**全非GPIO 直连**（经 100Ω 送到 CN3 由核心板采样）：
- SW2 → `PWR_RST`(CN3-35) 硬复位
- SW3 → `EMMC_KEY`(CN3-33) eMMC 复位
- SW4 → `PWR_KEY_DET`(CN3-43) **← 唯一可做电源唤醒键**
- SW5 → `ADC_KEY`(CN3-55) **`bom=no` 未贴**，SARADC 也悬空

→ 底板 DTS **不写按键节点**；`PWR_KEY_DET` 若核心板侧有GPIO，可在核心板 DT 做 power键。

### 2.8 运行灯 LED4（🟡 沿用厂商，但需改极性）

| 项 | 值 |
|---|---|
| GPIO | GPIOAO_10（✅ 与本板一致）|
| 驱动 | 厂商 `rp_power.run_led`，`gpio_function = <3>`（FLASH）|
| 本板极性 | **ACTIVE_HIGH**（Q8 NPN低边，高电平亮）|

⚠ 厂商节点里`gpio_num = <&gpio_ao GPIOAO_10 GPIO_ACTIVE_HIGH>` 极性**恰好正确**，但 `gpio_function = <3>` 是 FLASH 而非普通输出，需确认 `gpioleds` 节点（当前 `status="disabled"`）如何启用。

### 2.9 USB / HDMI / MT9700 / FUSB340

| 项 | 厂商现状 | 本板 | 动作 |
|---|---|---|---|
| `&usb2_phy_v2` / `&usb3_phy_v2` / `&dwc2_a` | 已配| USB2/USB3 | 沿用 |
| `rp_power.usb_pwr` | GPIOA_1 | — | 🟡 确认 |
| `rp_power.otg_pwr`/`otg_host` | GPIOZ_9 / GPIOZ_8 | MT9700 已改 EN 常开 | ✅ **GPIOAO_11 不需控制** |
| HDMI | 无专用节点 | CN4 连接器 + CEC 转换 | 🟡 确认是否需 CEC |
| FUSB340 SEL | ❌ 无配置 | **GPIOA_2**（LOW=USB3.0 / HIGH=PCIe）| 🔴 **新增** |
| SL6341D Hub | 无配置 | U31`bom=yes`，RSTN 有硬件复位 |✅ 不需 SoC 控制 |

---

## 三、待你拍板的 5 个决策点

| # | 问题 | 影响 |
|---|---|---|
| **1** | **U31(SL6341D) 在不在用？** | 决定 GPIOA_3 能否给屏 RST（厂商当 hub_rst 用）|
| **2** | **SPI_B SCLK 能否换脚？** | GPIOH_6 被厂商当 SPI cs + USB vbus |
| **3** | **喇叭/spk_on(GPIOA_4) 要不要？** | 决定该脚能否给屏 RS |
| **4** | **aml-4.9 的 realtek.c 是否支持 `rgmii-id` 双延时？** | 决定以太网能否工作 |
| **5** | **音频保留哪些？** | `pdm_codec`/`dummy_codec`/`eqdrc` 可否关闭 |

---

## 四、我建议的处置顺序

1. **注释 MIPI dtsi include**（pro-a311d.dts:7）→ 释放 GPIOA_2/A_8/A_9、GPIOH_4
2. **新增 SPI 节点 + pinctrl**（屏）—— 先解决 3 个 GPIO 冲突
3. **新增以太网 `&gmac0`**（`rgmii-id`, `reg=<1>`）
4. **新增 SHT40**（U42 一颗，走 `&i2c3`；U45 因信号线网表悬空未启用）
5. **新增 FUSB340 SEL（GPIOA_2）**
6. **&isp disabled**（摄像头未用）
7. 音频/按键/LED 按决策调整