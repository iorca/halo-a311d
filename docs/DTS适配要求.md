# MAIN_V0.3 — DTS 适配要求（按外设分类）

> SoC：Amlogic A311D（DTS 中为 `&{/soc/meson/g12b/g12b}` 系列节点）
> 底板：MAIN_V0.3，接插件 CN1/CN2/CN3 = `AXK5F80337YG`（80P BTB）
> 数据来源：**全工程** Protel2 网表（`nl_full_project.net`，495 元件 / 391 网络，13 页全导出），已按 `Add into BOM` + `Convert to PCB` 字段过滤

## 0. 关键修正（相对上一版）

| 项 | 上一版 | 本版（实测网表） |
|----|--------|----------------|
| 位号写法 | `CN230`/`CN345`（拼写臆造） | `CN2-30`/`CN3-45`（元件.引脚） |
| 以太网 PHY | RTL8211F（口述） | **U23 = YT8531H-CA**（板载实测） |
| 数据完整性 | 仅 power 页 | 全工程 13 页 |
| 幽灵器件 | 未过滤 | 已按 BOM/PCB 标记过滤 |

> **重要**：网表中 150 个器件标记为 `Add into BOM=no` / `Convert to PCB=no`，即"绘制了但未使用"。写 DTS 时**不得引用**这些器件。

## 1. GPIO 域归属规则

| 域 | DTS phandle | 引脚 |
|----|------------|------|
| EE 域 | `&gpio` | `GPIOA_*` / `GPIOC_*` / `GPIOH_*` / `GPIOX_*` |
| AO 域 | `&gpio_ao` | `GPIOAO_*` |

底板上 GPIO 的实际去向（共 23 条 GPIO 网络）：

| A311D引脚 | phandle | 底板连接 | 备注 |
|-----------|---------|----------|------|
| GPIOA_0 | `&gpio GPIOA_0` | CN2-30, R88, R92 | 4.7k+0Ω 串联 |
| GPIOA_1 | `&gpio GPIOA_1` | CN2-32, R89, R91 | 同上 |
| **GPIOA_2** | `&gpio GPIOA_2` | CN2-36, R86(0Ω), R87(4.7k), R85(4.7k) | **FUSB340 `.6=SEL`**，见 §8|
| GPIOA_3 | `&gpio GPIOA_3` | CN2-38, FPC5-3 | **普通GPIO**（非 SPI_B） |
| GPIOA_4 | `&gpio GPIOA_4` | CN2-40, FPC5-4 | **普通GPIO**（非 SPI_B） |
| GPIOA_6~12 | `&gpio GPIOA_x` | CN2-44/46/48/50/52/54/56 | 直连 BTB |
| **GPIOA_14** | `&gpio GPIOA_14` | CN2-62, **U42(SHT40).1**, FPC3-17 | `WORLD_SYNC`/`I2C_EE_M3_SDA`，见 §7.2 |
| **GPIOA_15** | `&gpio GPIOA_15` | CN2-64, **U42(SHT40).2**, FPC3-18 | `IR_REMOTE_IN`/`I2C_EE_M3_SCL`，见 §7.2 |
| GPIOC_7 | `&gpio GPIOC_7` | CN2-28, R90, R93 | |
| GPIOH_4 | `&gpio GPIOH_4` | CN2-10, FPC5-5, FPC3-26* | **SPI_B_MOSI**，*FPC3 未使用 |
| GPIOH_5 | `&gpio GPIOH_5` | CN2-12, FPC3-28* | **SPI_B_MISO** |
| GPIOH_6 | `&gpio GPIOH_6` | CN2-14, FPC5-8, FPC3-27* | **SPI_B_SCLK** |
| GPIOH_7 | `&gpio GPIOH_7` | CN2-16, FPC5-6, FPC3-29* | **SPI_B_SS0 (CS)** |
| **GPIOH_8** | `&gpio GPIOH_8` | CN2-18, **Q15基极(R165 1kΩ)** | **LCD_BL_EN 背光开关**，`GPIO_ACTIVE_LOW`(PNP高边)，见 §7.1 |
| **GPIOAO_5** | `&gpio_ao GPIOAO_5` | CN3-75, R116, **U38(IRM-V838M3)** | **红外接收头**，见 §6 |
| **GPIOAO_10** | `&gpio_ao GPIOAO_10` | CN3-37, R110(100Ω), **Q8 BASE** | **运行指示灯 LED4**，`GPIO_ACTIVE_HIGH`，见 §3.1 |
| **GPIOAO_6** | `&gpio_ao GPIOAO_6` | CN3-45, U9(1N5819WT) | AO 域，适合做唤醒 |
| **GPIOAO_11** | ~~`&gpio_ao GPIOAO_11`~~ | CN3-79, **U8(MT9700).4 = EN**, R158(10kΩ) | ⚠**EN 改电阻上拉常开，GPIO 已释放** → §10.1 |
| **GPIOX_6** | `&gpio GPIOX_6` | CN3-40, **U40(AP6256)-12** | WiFi 控制 |
| **GPIOX_7** | `&gpio GPIOX_7` | CN3-42, **U40(AP6256)-13** | BT 控制 |
| **GPIOX_19** | `&gpio GPIOX_19` | CN3-38, **U40(AP6256)-6** | WiFi/BT 使能 |

---

## 2. 按键（SW2/SW3/SW4 = TSA020B3440A02 贴片按键）

**四个按键全部经电阻上拉到 CN3，由核心板采样——没有一个是 A311D 本地 GPIO 直连。**
（阻值取网表 `={Value}` 字段，非型号编码）

| 位号 | 按下后的网络 | 串阻(Value) | 去向(CN3) | 判定功能 |
|------|--------------|-----------|-----------|----------|
| SW2 | `$5N584`（SW2-2 + D6 + C162） | R112 **100Ω** | **PWR_RST** → CN3-35 | **系统复位键** |
| SW3 | `EMMC_KEY_B`（SW3-2 + D7） | R113 **100Ω** | **EMMC_KEY** → CN3-33 | **eMMC 复位键** |
| SW4 | `$5N591`（SW4-2 + D8） | R114 **100Ω** | **PWR_KEY_DET** → CN3-43 | **电源/唤醒键** |
| SW5 | `$5N594`（SW5-2 + R118 + C163） | R118 **100Ω** | **ADC_KEY** → CN3-55 | **ADC 键** ⚠`Add into BOM=no` |

**DTS 结论**
- `PWR_KEY_DET`(SW4) 是唯一适合做**系统唤醒**的键 → 核心板侧配 `gpio-keys` 的 `power` 键（若为常闭需 `wakeup-source`）。底板仅 1k 上拉+ESD(D8)，**底板 DTS 不写按键节点**。
- `PWR_RST`(SW2) 是硬复位，走核心板复位引脚，**不进设备树**。
- `EMMC_KEY`(SW3) 是 eMMC 复位，核心板侧处理。
- SW5 未贴（`Add into BOM=no`），`ADC_KEY` 实际不装配 → **不要写 adc-keys**，除非后续贴上 SW5。
- 所有按键均**非** GPIO 直连 → 底板 DTS **不含 `gpio-keys` 节点**。

## 3. 指示灯（LED1~LED4，NCD0402G1 / VLMB1500）

| 位号 | 型号 | 说明 |
|------|------|------|
| LED1, LED2, LED3 | NCD0402G1 | 电源/状态指示，直接接在电源与地之间，**无 GPIO 控制** |
| **LED4** | **VLMB1500-GS08** | **运行指示灯（RUN）**，由 **Q8(GPIOAO_10)** 控制 |

### 3.1 运行指示灯 LED4（Q8 = PMBS3904，**NPN**）

> ⚠ **型号事实（规格书实锤）**：`PMBS3904,215-JSM` = **NPN SWITCHING TRANSISTOR**（杰盛微 JSM）。
> SOT-23 引脚：**1=BASE, 2=EMITTER, 3=COLLECTOR**。互补料为 `MMBT3906`（PNP）。
>型号里的 "PM" **不代表 P-MOS**，勿凭型号名判断极性。

**网表实测链路（标准 NPN 低边开关）**

```
A_3V3 ── R108(4.7kΩ) ── LED4.2
LED4.1 ── Q8.3 (COLLECTOR)
Q8.2 (EMITTER) ── GND
Q8.1 (BASE) ── R110(100Ω) ── CN3.37 (SYS_LED) ── 核心板 GPIOAO_10
```

**极性判定**

| GPIOAO_10 | Q8 (NPN) | LED4 |
|-----------|-----------|------|
| **HIGH (1)** | Base 注入电流 → 导通 | **点亮** |
| LOW (0) | 截止 | 熄灭 |

→ **`GPIO_ACTIVE_HIGH`**（高电平亮）

R110=100Ω（基极限流），R108=4.7kΩ（LED 限流）。
LED1/LED2/LED3 无 GPIO 控制 → DTS 不写对应 gpio-leds。

> ⚠ **Q8 与 Q15 料号不同、极性相反**：Q8 = **NPN 低边**（高电平亮）、Q15 = **PNP 高边**（低电平亮）。写 DTS 别搞混。

## 4. 以太网 RGMII（U23 = YT8531H-CA）

**PHY 侧信号（底板 → CN3 → 核心板 GMAC0）**

| PHY 引脚 | 网络 | CN3 引脚 |
|---------|------|---------|
| RGMII_MDC (13) | RGMII_MDC | CN3-6 |
| RGMII_MDIO (14) | RGMII_MDIO | CN3-8 |
| GMAC0_TXD3/2/1/0 (15-18) | → R58/R57/R56/R55 | 经 CN3 |
| GMAC0_TXEN (19) | → R53 | |
| GMAC0_TXCLK (20) | → R54 | |
| PHY0_RXD3/RXD2/RXD1/RXD0 (22-25) | → R65/R64/R63/R62 | |
| PHY0_RXDV (26) | → R60 | |
| PHY0_RXCLK (27) | → R61 | |
| PHY0_RSTN (12) | PHY0_RSTN | R48(1.8k)+R50(0Ω)，**本地复位** |
| PHY0_INT_N (31) | PHY0_INT_N | R49 |
| PHY0_CLKOUT125 (35) | R44/R43 | 125MHz 时钟 |

**DTS 用 `&gmac0`（`GMAC0_*` 命名）+ 外部 PHY；compatible 用 `ethernet-phy-ieee802.3-c22`（通用 C22 PHY 绑定）。**

> **PHY 型号 = U23 = YT8531H-CA（裕太微），Pin-to-Pin 兼容 RTL8211F，两者可互换。**
>
> | | YT8531C | RTL8211F |
> |---|---|---|
> | 工艺 | 55nm | 65nm |
> | 功耗@1000M | ~420mW | ~450mW |
> | 温度 | **-40~85℃** | 0~70℃ |
> | 接口 | RGMII/RTBI | RGMII/RTBI |
>
> → **YT8531 功耗、温度、ESD 全面更优**，是 RTL8211F 的国产 pin-to-pin 替代料。
>
> **⚠ YT8531 最大的坑 —— RGMII 延时（`rgmii-id`）**
> YT8531 常需 `phy-mode = "rgmii-id"`（MAC 与 PHY 各提供约 2ns 延时）。
> 由 strap 电阻决定：`RGMII_RXD0/RXDLY` 上拉 → RX 延时开；`RGMII_RXD1/TXDLY` 下拉 → TX 延时关。
> 本板 R62~R65 + R75/R77/R79/R80 已配这些 strap（见上表）。
> **mainline 已内置 `CONFIG_MOTORCOMM_PHY` 驱动**，无需移植。
> 验证：`dmesg` 应打印 `driver [Motorcomm YT8531]`；若显示 RTL8211F 说明 PHY ID 读取异常。

**PHY 复位（R50 = 0Ω 直通，实测确认为同一路）**
```
RGMII_RST# (CN3-2, 核心板来) ──R50(0Ω)──→ PHY0_RSTN (U23-12)
```
- 核心板拉低 `RGMII_RST#` 即复位 PHY；底板 DTS **无需**再配 PHY 复位 GPIO。
- `PHY0_RSTN` 另挂 R48(**1.8kΩ**) 上拉。

**PHY0_LED0/CFG_EXT(.32)、PHY0_LED1/CFG_LDO0(.33) = 硬件 strap 复用**
- 上电瞬间为 **CFG**（采样配置），延时后转为 **LED**（RJ45 指示灯）；
- 由 R67/R69/R72 电阻决定采样电平 → 属**硬件 strap**，DTS **不需要**任何配置；
- DTS 只需保证 `phy-mode = "rgmii";` 与实际一致。

- PHY 地址：`PHY0_RXD*/PHYAD*` 复用脚带配置电阻（R78/R71/R77/R75/R80/R79），硬件定址 → DTS 填 `phy-address`。
- **本板以太网 = RGMII 千兆（1000M）**：`GMAC0` + U23(YT8531H-CA)，走 `&gmac0` + `&mdio`。
- **唯一以太网口，无 RMII**（RGMII/RMII 互斥，见 §7.0.2）。

## 5. HDMI（CN4 = HYC70-HDMIA19-230）

| 信号 | 网络 | 备注 |
|------|------|------|
| HPD | HDMI_HPD → CN1-47 | R35/R36 分压+C51 |
| CEC | HDMI_TX_CEC → CN1-53 | 经 Q5(MS3134) 双向电平转换 |
| SCL | HDMI_TX_SCL → CN1-51 | 经 Q6 |
| SDA | HDMI_TX_SDA → CN1-49 | 经 Q7 |
| HotPlug | HDMI_HOTPLUG | CN4-19, D4 ESD, R35 |
| CEC 侧 | HDMI_CEC | CN1-53 |

- HDMI 主控在核心板（A311D 的 dw_hdmi），底板只做**连接器 + CEC 双向转换 + ESD**。
- DTS：`&hdmi_tx` + `&cec`(CEC GPIO 复用)；HPD 为 GPIO 输入。
- MS3134 = **双向 I2C 电平转换**（HDMI 5V↔3.3V），非隔离器。

## 6. 红外 IR（U38 = IRM-V838M3-C/TR1 → GPIOAO_5）

**网表实测链路**

```
U38 IRM-V838M3-C/TR1 (SOT-23, 红外接收头)
  .1 = GND
  .2 = A_3V3
  .3 = 输出 → R116 → R115 → CN3-75 (IR_IN) → 核心板 GPIOAO_5
```

**A311D 引脚：`GPIOAO_5`（复用名 `IR_REMOTE_IN` / `PWMAO_D`）**

| 项 | 值 |
|---|---|
| DTS 引用 | `&gpio_ao GPIOAO_5` |
| 域 | **AO 域**（always-on，休眠时保持 → 可做唤醒源） |
| 网络 | `IR_IN` → CN3-75 |
| 串联电阻 | R116(FRC0402F1000TS) + R115 |

**DTS 要求**
```
&ir {
    status = "okay";
    gpios = <&gpio_ao GPIOAO_5 GPIO_ACTIVE_LOW>;
};
```
> `GPIOAO_5` 需配 `bias-pull-up`（红外接收头输出为开漏/拉低脉冲），AO 域保证休眠唤醒。
> AP6256 的 `GPIOX_6/7/19` 与 IR 无关（那是 WiFi/BT 使能）。

## 7. SPI（SPI_B — SPI 屏幕，走 FPC5）

**FPC5 座 = SPI 屏幕模块**（用户确认）。信号经 CN2 桥接：核心板 SoC pad ↔ CN2 pin ↔ FPC5。

**CN2 桥接对照（用户提供核心板原理图）**

| CN2 pin | 核心板侧信号 | 核心板侧功能 | → FPC5 pin |
|---------|------------|-------------|-----------|
| 10 | `GPIOH_4` | `SPI_B_MOSI` | .5 |
| 12 | `GPIOH_5` | `SPI_B_MISO` | — |
| 14 | `UART_EE_C_RX` | `SPI_B_SS0` (CS) | — |
| 16 | `UART_EE_C_TX` | `SPI_B_SCLK` | — |
| 18 | `LCD_BL_EN` | `GPIOH_8` | — |

**核心板信号 → A311D 引脚 → DTS 引用**（**仅 GPIOH 组，GPIOA_3/4 不参与 SPI_B**）

| 核心板信号 | A311D 引脚 | DTS 引用 | FPC5 |
|-----------|-----------|---------|-------|
| `SPI_B_MOSI` | **GPIOH_4** | `&gpio GPIOH_4` | .5 |
| `SPI_B_MISO` | **GPIOH_5** | `&gpio GPIOH_5` | — |
| `SPI_B_SS0` (CS) | **GPIOH_7** | `&gpio GPIOH_7` | .6 |
| `SPI_B_SCLK` | **GPIOH_6** | `&gpio GPIOH_6` | .8 |
| `LCD_BL_EN` / `SPI_LEDA` | **GPIOH_8** | `&gpio GPIOH_8` | .1 |

### 7.0 屏幕模组的 RST/RS —— GPIOA_3 / GPIOA_4（**普通 GPIO，不是 SoC SPI 复用**）

**这里必须讲清楚一个命名陷阱**：

`SPI_RST` / `SPI_RS` 只是**给 FPC5 上那个 SPI 屏模组的统一信号命名**，
**与 A311D SoC 的 SPI 硬件功能无关**，不需要任何 SPI mux 配置。

| 屏幕信号 | A311D 引脚 | SoC 规格书复用名 | DTS 用法 | FPC5 |
|---------|-----------|----------------|---------|-------|
| `SPI_RST` | **GPIOA_3** | `TDMB_D0` / `TDMB_DIN0`（第三功能 `-`） | **普通 GPIO 输出** | .3 |
| `SPI_RS` (Reg Select) | **GPIOA_4** | `TDMB_D1` / `TDMB_DIN1` / **`PWM_D`** | **普通 GPIO 输出** | .4 |

- 规格书列出复用名**不代表启用了该功能**；此处 GPIO mux 保持默认 GPIO 模式。
- DTS 里**当作普通 GPIO 声明**（`gpios` 属性）即可，**不需要 pinctrl / mux 配置**。
- 屏模组自己吃这两根做复位和寄存器选择，SoC 只负责拉电平。
- ⚠ **GPIOA_2 也有复用**：`TDMB_FS` / `TDMB_SLV_FS`（TDM 帧同步）。
  本板 GPIOA_2 已用作 **FUSB340 `.6=SEL`**（§8）——**若日后启用 TDM 音频，FS 会占用 GPIOA_2，FUSB340 切换需换脚**。

**DTS 写法**
```
&gpio_ctrl {
    /* FPC5 SPI 屏：复位 + 寄存器选择（非 SPI 硬件功能） */
    lcd-rst-gpios  = <&gpio GPIOA_3 GPIO_ACTIVE_HIGH>;  /* 实际极性按屏手册 */
    lcd-rs-gpios   = <&gpio GPIOA_4 GPIO_ACTIVE_HIGH>;
};
```
> ⚠ 极性需按屏模组手册定；此处 GPIOA_3/4 与 FPC5-3/4 的对应已在 §7 表中列出。

### 7.0.1 GPIO 电压域（规格书确认）

| 电压轨 | 值 | 供电组 | 底板去向 |
|--------|-----|--------|----------|
| `VDDIO_X` | **1.8V** | 取自 `VDDIO_AO18` | CN3-58（经 R170(0Ω)） |
| `ETH_VDDIO` | **3.3V** | **GPIOZ 组** | CN3-34 → R26/R27(0Ω) → PHY IO 域 |

- `VDDIO_X`（GPIOX 组，含 GPIOX_6/7/19 三个 WiFi 控制脚）= **1.8V**
- `ETH_VDDIO`（PHY 的 RGMII IO 域）= **3.3V**
- ⚠ 两者是**不同电压域**，不可混用；PHY strap 电阻(R26/R27/R51/R52)挂在 3.3V 域。

### 7.0.2 RGMII 与 RMII 互斥（A311D 规格书 PRG_ETH_REG1 确认）

**`PRG_ETH_REG1` (0xff634544) bit[0] = PHY Interface Select**

| bit[0] | 内部值 | 模式 |
|--------|--------|------|
| **1** | 001 | **RGMII** |
| **0** | 100 | **RMII** |

>规格书原文：**"These pins select one of the multiple PHY interfaces of MAC.
> This is sampled only during reset assertion and ignored after that."**

**结论：RGMII 与 RMII 完全互斥，且只能在复位时采样确定，运行中无法切换。**

| 维度 | 说明 |
|------|------|
| **物理互斥** | 同一 GMAC，pad 组不同（RGMII 4bit+TXC/RXC，RMII 2bit+REF_CLK），同一时刻仅一种 |
| **寄存器互斥** | `PRG_ETH_REG1[0]` 二选一，写 1=RGMII / 0=RMII |
| **时序限制** | **仅在复位断言时采样**，之后忽略寄存器写入 → 运行中改寄存器无效 |

**本板确定使用 RGMII（1000M），不使用 RMII。**
- `&gmac0` = RGMII 千兆 + 外部 PHY U23(YT8531H-CA) → **本板唯一以太网口**
- 复位时 `PRG_ETH_REG1[0]=1` 锁定 RGMII，运行中无法改。

### 7.0.3 A311D MAC 侧可控 RGMII TX 延迟

**`PRG_ETH_REG1` (0xff634544) bit[6:5] — TX_CLK 相对 TXD 的延迟**

| bit[6:5] | 延迟 | @125MHz 折算 |
|----------|------|-------------|
| 00 | 0 cycle | 0ns |
| **01** | **¼ cycle** | **≈2ns** |
| 10 | ½ cycle | ≈4ns |
| 11 | ¾ cycle | ≈6ns |

RGMII 规范要求 **2ns** 的 TX 时钟偏移，可在 MAC 侧或 PHY 侧提供（**二选一，不叠加**）。

**Linux DTS 写法（不要直接写寄存器，用 stmmac 的 phy-mode）**

| phy-mode | 含义 |
|----------|------|
| `rgmii` | 两侧都不加延迟 |
| **`rgmii-id`** | **MAC 侧加 TX+RX 延迟**（→ 驱动设 bit[6:5]=01）|
| `rgmii-txid` | 仅 MAC 侧加 TX 延迟 |
| `rgmii-rxid` | 仅 MAC 侧加 RX 延迟 |

- **本板建议 `rgmii-id`**：YT8531 常需 2ns 偏移；由 strap 电阻（R62~R65、R75/R77/R79/R80）决定实际生效位置。
- 驱动：`mainline` 已内置 `CONFIG_MOTORCOMM_PHY`。
- 验证：`dmesg` 应打印 `driver [Motorcomm YT8531]`；PHY ID 应为 `0x0000011a`(Motorcomm)。

**FPC5 座（5001-FPC0520-08R1-00-B）**

| FPC5 | 网络 | 说明 |
|------|------|------|
| .1 | SPI_LEDA | R164(**10Ω**) 串阻 → **Q15(MMBT3906 PNP) 集电极** |
| .2 | GND | |
| .3 | GPIOA_3 | **SPI 屏 `SPI_RST`**（普通GPIO，核心板复用名 `TDMB_D0`） |
| .4 | GPIOA_4 | **SPI 屏 `SPI_RS`**（普通GPIO，核心板复用名 `TDMB_D1`） |
| .5 | GPIOH_4 | **SPI_B_MOSI** |
| .6 | GPIOH_7 | **SPI_B_SS0 (CS)** |
| .7 | A_3V3 | |
| .8 | GPIOH_6 | **SPI_B_SCLK** |

> ✅ 已闭环：`SPI_RST`=`GPIOA_3`、`SPI_RS`=`GPIOA_4`，**均为普通 GPIO**，SoC 无 SPI 复用（见 §7.0）。

### 7.1 背光控制（GPIOH_8 → Q15 = **MMBT3906，PNP 高边**）

> ✅ **料号已确认（用户核对）**：Q15 应贴 **MMBT3906（PNP）**。
> 原网表 `PMBS3904,215-JSM`（NPN）是**复制粘贴错误**——规格书明确 PMBS3904 的互补料正是 MMBT3906。

**网表实测链路（阻值取 `={Value}` 字段）**

```
GPIOH_8 (CN2-18)
   └─ R165 (1kΩ) → Q15.1  (BASE)
Q15 = MMBT3906 (SOT-23, **PNP**)  ← 高边开关
   .1 = BASE      ← R165(1kΩ) ← GPIOH_8
   .2 = EMITTER   ← A_3V3           (Emitter 接高电位 = PNP 正确接法)
   .3 = COLLECTOR → R164(10Ω) → SPI_LEDA → FPC5.1   (输出 → 屏幕背光)
```

**逻辑极性（PNP 高边开关，Base 拉低才导通）**

| GPIOH_8 | V_BE | Q15 | SPI_LEDA |
|---------|------|-----|----------|
| **LOW (0)** | −0.7V | **导通** | **A_3V3 → 背光点亮** |
| HIGH (1) | 0 | 截止 | 高阻 → 背光灭 |

**DTS 要求**
```
&gpio_ctrl {
    backlight-gpios = <&gpio GPIOH_8 GPIO_ACTIVE_LOW>;  /* 0=背光开, 1=背光灭 */
};
```
> Q15 只做**硬开关**，非 PWM 调光。亮度调节需屏模组自身支持 PWM/DAC。

**⚠ 制板注意**：Q15 **必须贴 MMBT3906（PNP）**，不能贴 PMBS3904（NPN）。
若误贴 NPN：Emitter 接 A_3V3 使 `V_BE` 需 4.0V > A311D GPIO 上限 3.3V → **恒截止、背光不亮**。

**Q8（运行灯）对比**：Emitter 接 GND，是标准 **NPN** 低边 → `GPIO_ACTIVE_HIGH`（高亮）。
→ Q8(NPN,低边) 与 Q15(PNP,高边) **料号不同、极性相反**，写 DTS 别搞混。

**I2C 三条总线（全部经CN3 到核心板 + 电平转换 MS3134）**

| 总线 | 网络 | CN3 | 转换 |
|------|------|-----|------|
| `I2C_AO_M0` | SDA/SCL | CN3-69/71 | Q13/Q14 (MS3134) → 摄像头 FPC2-22/23（**摄像头未用，见§12**） |
| `I2C_EE_M2` | SDA/SCL | CN3-63/65 | 直通（M.2） |
| HDMI CEC | — | CN1 | Q6/Q7 |

- DTS：`&i2c_A`(AO)、`&i2c_E`(EE)；`I2C_AO_M0` 属 AO 域→`&i2c_A`。

### 7.2 触控 I2C + SHT40 温湿（GPIOA_14/A15）

**实测链路（走 CN2，不是 CN3）**

```
TOUCH_I2C_SDA = CN2-62 + FPC3-17[未贴] + U42(SHT40).1
TOUCH_I2C_SCL = CN2-64 + FPC3-18[未贴] + U42(SHT40).2

U42 = SHT40-CD1B-R3 (温湿度传感器, I2C 地址 0x44)
  .1 = SDA  .2 = SCL  .3 = A_3V3  .4/.5 = GND
```

**A311D 引脚**

| 功能 | A311D 引脚 | 复用名 | DTS 引用 |
|------|-----------|--------|---------|
| `TOUCH_I2C_SDA` | **GPIOA_14** | `WORLD_SYNC` / `I2C_EE_M3_SDA` | `&gpio GPIOA_14` |
| `TOUCH_I2C_SCL` | **GPIOA_15** | `IR_REMOTE_IN` / `I2C_EE_M3_SCL` | `&gpio GPIOA_15` |

>复用名来自核心板侧标注（`WORLD_SYNC`、`IR_REMOTE_IN` 是同 pad 的其它功能）。
> **注意别混淆**：红外接收头用 `GPIOAO_5`（§6）；此处 `GPIOA_15` 的复用名也叫 `IR_REMOTE_IN`，但不是同一脚。

**DTS 要求**
```
&i2c_ee_m3 {
    status = "okay";
    /* 触控屏(可选) + SHT40 共用此总线 */
    sht40: sht40@44 {
        compatible = "sensirion,sht4x";
        reg = <0x44>;
        status = "okay";
    };
};
```
- FPC3 座（触控屏）目前 `Add into BOM=no`（未贴），若后续贴上（如 GT911）再加节点，共用同一 `&i2c_ee_m3`，不同 reg 地址。

### 7.3 第二颗 SHT40 —— **U45 @ `I2C_AO_S0`（AO 域）** ✅ 两条总线**都启用**

> ✅ **网表终版确认（2026 重新导出核验）**：U42 与 U45 **两颗 SHT40 均 `Add into BOM=yes`，同时贴装**。
> 此前"二选一"的判断已作废 —— 它们在**两个独立 I2C 控制器**上，同地址 0x44 **合法共存**。

**实测链路**

```
I2C_AO_S0_SDA = U45.1
I2C_AO_S0_SCL = U45.2
U45 = SHT40-CD1B-R3   (bom=yes)
  .1 = SDA   .2 = SCL   .3 = VDDIO_AO18(1.8V)   .4/.5 = GND
配套 C218 (CL05B104KB54PNC, bom=yes) 挂 VDDIO_AO18 / GND 去耦
```

**两颗对照**

| 项 | **U42**（§7.2） | **U45**（本节） |
|---|---|---|
| 总线 | `TOUCH_I2C` | `I2C_AO_S0` |
| A311D 引脚 | GPIOA_14 / GPIOA_15 | AO 域 I2C（经 CN3） |
| 底板出口 | CN2-62 / CN2-64 | CN3 |
| 供电 | `A_3V3` | **`VDDIO_AO18`（1.8V）** |
| 同伴器件 | FPC3 触控座（未贴） | C218 去耦 |
| 地址 | 0x44 | 0x44（**不同控制器，不冲突**）|

**DTS 写法（两条都okay）**
```
/* U42：EE 域 I2C（GPIOA_14/15），与触控屏共用 */
&i2c_ee_m3 {
    status = "okay";
    sht40_ee: sht40@44 {
        compatible = "sensirion,sht4x";
        reg = <0x44>;
    };
    /* 若后续贴 FPC3 触控屏（如 GT911），在此追加不同 reg 节点 */
};

/* U45：AO 域 I2C，休眠仍可采样 */
&i2c_ao_s0 {
    status = "okay";
    sht40_ao: sht40@44 {
        compatible = "sensirion,sht4x";
        reg = <0x44>;
    };
};
```

- **关键**：两者是**不同 I2C 控制器**，同 `reg = <0x44>` 完全合法。
- U45 挂AO 域 → 系统休眠时仍可读温湿度。
- ⚠ 若把两颗挂到**同一个** `&i2c` 控制器下 → 地址冲突，总线锁死。
- 原 `I2C_AO_M0_SDA/SCL`（CN3-69/71，经 Q13/Q14 MS3134）仍为**未使用**（Q13/Q14 `bom=no`），那条是通摄像头的，本次未用。

## 8. PCIe / USB3.0 切换（U28 = FUSB340TMX）★

**这是你指定的 GPIOA_2 切换功能，链路已确认：**

```
GPIOA_2 → CN2-36 → R86(0Ω) → PCIE_EN → U28(FUSB340).6
```

**U28 FUSB340TMX（TMLP-18）引脚**

| 引脚 | 网络 | 对端 |
|------|------|------|
| .6 | PCIE_EN | R86 ← GPIOA_2 |
| .10/.11 | A311D_TP / A311D_TN | 核心板 PCIe TX（电容 C116/C117） |
| .15/.16 | A311D_RP / A311D_RN | 核心板 PCIe RX（电容 C122/C124） |
| .1/.2 | C_RX0_N / C_RX0_P | **U30(USB3 控制器)-1/2** |
| .4/.5 | C_TX0_N / C_TX0_P | **U30-4/5** |
| .13/.14 | PCIE_RX0P/N | U30-10/11 |
| .8/.9 | PCIE_TX0P/N | U30-8/9 |

**级联链**：`A311D ←PCIe→ FUSB340(U28) ←SuperSpeed→ FSW3410(U30) ←→ USB3_SS* → USB2`

### 8.1 FUSB340 控制脚（用户确认 + 网表核对）

**U28(FUSB340TMX) 控制脚 = `.6=SEL` + `.7=OE`**

| 引脚 | 功能 | 板上接法 | 状态 |
|------|------|----------|------|
| **.6** | **SEL**（Switch Select） | R86(0Ω) → `GPIOA_2` | **SoC 可控，运行时可切 SW1/SW2** |
| **.7** | **OE**（Output Enable） | 直接接 **GND** | 恒使能（0 = Switches Enabled） |

**Truth Table 对照（0=SW1=USB3.0, 1=SW2=PCIe）**

| `_EN`(OE, 恒0) | `SEL`(GPIOA_2) | 结果 |
|---|---|---|
| Low | **Low** | TX1/RX1 → **SW1 = USB3.0** |
| Low | **High** | TX2/RX2 → **SW2 = PCIe** |

**结论：GPIOA_2 = 完整的 PCIe↔USB3.0 运行时切换脚，硬件完全支持，无需改板。**
- `GPIOA_2 = LOW` → USB3.0（默认，因 R85/R87 4.7k 下拉）
- `GPIOA_2 = HIGH` → PCIe
- OE 恒接地 → 开关永不禁用，TX/RX 不会进 Hi-Z（除非上电前 SEL 悬空）

**DTS 要求**
```
&gpio_ctrl {
    fusb340-sel-gpios = <&gpio GPIOA_2 GPIO_ACTIVE_HIGH>;  /* 0=USB3.0, 1=PCIe */
};
```

## 9. SDMMC / SD / eMMC

| 信号 | 网络 | 去向 |
|------|------|------|
| SD_CLK | SD_CLK | CN2-55 → CARD1-5 |
| SD_CMD | SD_CMD_B | CN2-59 → CARD1-3 |
| SD_D0~D3 | SD_D0_B~SD_D3_B | CN2-51/53/61/63 → CARD1 |
| 复位 | EMMC_KEY_B | SW3 |

- SD 卡= `&sd_emmc_c`(CN1)；CARD1 为 SD 座（经 ESD U35/U36/U37）。
- eMMC 在**核心板**，底板只出复位键。

## 10. WiFi/BT —— AP6256（U40）

| U40 引脚 | 网络 | 说明 |
|---------|------|------|
| .12 | GPIOX_6 | **WiFi 使能**（A311D 控） |
| .13 | GPIOX_7 | **BT 控制**（A311D 控） |
| .6 | GPIOX_19 | WiFi/BT 电源/总使能 |
| .16~.19, .14/.15 | WIFI_SD_CMD/D0~D3 | **SDIO**→ CN3-44~54 → 核心板 |
| .34 | BT_EN | R147(4.7k)+R145(3.3k) → CN2-58（`BT_EN_3V3`） |
| .7 | BT_WAKE_HOST | U39(1N5819) → CN2-42（`BT_WAKE_HOST_3V3`） |
| .41~.44 | BTUART_A_* | UART→ CN3-74~80 |
| .25~.28 | BTPCM_* | PCM→ CN3-64~70 |
| .2 | WIFI0 | 射频 |

**DTS 要求**：
- SDIO 走 `&sdio`（核心板），底板仅把信号经 CN3 引出，AP6256 本身不需独立 DT 节点（在核心板 DT 声明 `brcmfmac/ap6256`）；
- 电源使能 GPIO（`GPIOX_6/7/19`）配 `&gpio` 的 gpio-leds 或 regulator enable；
- `BT_EN` / `BT_WAKE_HOST` 为 **3.3V 逻辑**（经二极管到 CN2），若挂 AO 域可做唤醒源。

---

## 10.1 USB OTG 供电开关 —— U8 MT9700（**改为硬件常开，GPIOAO_11 释放**）

>✅ **设计定案（用户决定）**：MT9700 的 EN **不再用 GPIOAO_11 控制**，改为**电阻上拉常开**。

### 芯片定位

MT9700 = **单P-MOS 负载开关**（Aerosemi），80mΩ，USB VBUS 供电用。**无I2C/寄存器，无 Linux 驱动。**

### 引脚（规格书 PIN DESCRIPTION）

| 引脚 | 名称 | 本板连接 | 功能 |
|------|------|----------|------|
| 1 | VOUT | `5V_OTG` → USB4(MC-711) VBUS | 开关输出 |
| 2 | GND | GND | 地|
| 3 | **SET** | `MT9700_SET` → **R159(6.8kΩ)** → 地 | **限流阈值设定** |
| **4** | **EN** | ← **R158(10kΩ) 上拉**（改后） | **使能：高电平导通** |
| 5 | VIN | VCC5V 侧 | 输入（需10µF+ 陶瓷电容） |

### 内置保护（规格书参数）

| 保护项 | 参数 | 值 |
|--------|------|---|
| **限流** | ILIM @RSET=6.8kΩ | **0.75 / 1 / 1.25 A**（min/typ/max）|
| | 可调范围 | **0.4A ~ 2A** |
| **反向电流阻断** | — | 有（防反灌，USB 供电关键）|
| **热关断** | TSD | **135°C**（迟滞 20°C）|
| **欠压锁定** | UVLO | **2.2V**（迟滞 0.1V）|
| EN 阈值 | VIL / VIH | ≤0.8V / ≥2.0V |
| EN 内部下拉 | RDS(EN=0) | **200Ω** |
| 关断静态电流 | IQ(OFF) | <1µA |

**本板限流值：R159 = 6.8kΩ → ILIM ≈ 1A（typ）**，符合 USB 供电规范。

### 硬件常开改法

```
改前： GPIOAO_11 ──R158(10kΩ)── EN(4)
改后： VCC5V ────R158(10kΩ)── EN(4)      ← 上拉常开，MT9700 恒导通
```

- EN 高电平（≥2.0V）→ 开关导通，`5V_OTG` 输出 5V
- **EN 内部已有 200Ω 下拉**，改前GPIO 悬空时会拉到 <0.8V → 关断（安全默认）
- 改后 R158 上拉，**永久导通**，不再受软件控制

### DTS 影响：✅ 无需任何节点

```
/* MT9700 无需 DTS 节点 —— 硬件常开，保护全靠 R159 限流 + 内置反灌/热保护 */
```

- MT9700 是纯模拟开关，**没有 I2C/寄存器，不存在 Linux 驱动**
- 不写 `regulator` 节点、不写GPIO 控制、不占用 `GPIOAO_11`
- **GPIOAO_11 释放**，可另作他用（AO 域，注意其与休眠域逻辑）

> ⚠ 唯一风险：USB4 口恒定带 5V。若需 USB-C 双向插拔时防反灌给设备供电，
> 依赖 MT9700 **内置反向电流阻断**（规格书已含），一般无需软件介入。

## 11. DTS 编写优先级清单

| 优先级 | 节点 | 关键动作 |
|--------|------|---------|
| P0 | `&gmac0` | `phy-mode="rgmii-id"`（YT8531 需延时），复位用核心板 `RGMII_RST#` |
| P0 | `&hdmi_tx` + `&cec` | HPD/CEC/SCL/SDA GPIO |
| P0 | `&pcie` + FUSB340 | `GPIOA_2` = **FUSB340 `.6=SEL`**：LOW=SW1=USB3.0、HIGH=SW2=PCIe；`.7=OE` 恒接地 |
| P1 | `&dsi`（显示） | MIPI DSI 走 FPC3 |
| P1 | `&sdio`（AP6256） | **仅 1 个 SDIO = `&sd_emmc_a`**（A311D 仅一个 SDIO 控制器） |
| P1 | `&ir` | `GPIOAO_5`，`GPIO_ACTIVE_LOW` |
| P1 | `&i2c_ee_m3` / `&i2c_ao_s0` | **两颗 SHT40 都启用**（U42/U45，同 0x44 不同控制器）→ §7.2 / §7.3 |
| P1 | `&spi_B` | MOSI=GPIOH_4/MISO=GPIOH_5/CS=GPIOH_7/SCLK=GPIOH_6 |
| P1 | 屏控制 GPIO | RST=GPIOA_3、RS=GPIOA_4（普通GPIO）、背光=GPIOH_8（**ACTIVE_LOW**，PNP高边）|
| P2 | `leds` | LED4 运行灯 = GPIOAO_10（**ACTIVE_HIGH**）；LED1~3 无 GPIO 不写 |
| P2 | `&sd_emmc_c` / SD | SD 卡 |
| P2 | USB3 Hub | U31=SL6341D（`bom=yes`），**不需要 A311D 控制** |
| — | **无需节点**：MT9700 | EN 硬件上拉常开，**不占 GPIOAO_11**，无驱动 → §10.1 |
| — | **屏蔽**：摄像头 `&csi` | 摄像头未使用 |
| — | **屏蔽**：摄像头 `&csi` | 摄像头未使用 |
| — | **屏蔽**：gpio-keys | 4 个键全非 GPIO 直连（SW4 可在核心板做唤醒） |
| — | 屏蔽未用器件 | SW5、U4、U30、FPC2/FPC3-CSI 等（BOM=no） |

## 12. 补充：CN1（核心板 BTB）功能信号全表

底板 CN1 上除电源外，全部是**送往核心板的信号**，DTS 里对应核心板引脚：

| 类别 | CN1 引脚 | 网络 |
|------|----------|------|
| MIPI-CSI（摄像头） | CN1-28/30/34/36/40/42/46/48/52/54/58/60 | `MIPI_CSI_CLK*` / `MIPI_CSI_D0~D3` → FPC2 ⚠**摄像头未使用，不写 DTS** |
| MIPI-DSI（显示） | CN1-7/9/11/13/15/17/19/21/25/27 | `MIPI_D0~D3` + `MIPI_CLK` → FPC3 |
| HDMI | CN1-47/49/51/53 | `HDMI_HPD` / `_SDA` / `_SCL` / `_CEC` |
| 音频 | CN1-37/39/41/43, CN1-31/33 | `AL_CH_P/N`、`AR_CH_P/N`、`CVBS`、`AGND_CVBS` |

> **摄像头（用户确认：未使用）**：`&csi` / `&csi2` 节点**不写**；`CAMERA_RST/RST2`、`CM_RST/CM_PWRDN`、
> `I2C2_SCL_CAM/SDA_CAM`(Q13/Q14)、FPC2 全部信号一律不引用。
> **MIPI-DSI 显示**走 FPC3，正常使用。

## 13. 已确认事项（用户答复，闭环）
1. ✅ **FUSB340 控制脚 = `.6=SEL` + `.7=OE`**。`.7=OE` 直接接GND（恒使能，0=Switches Enabled）；`.6=SEL` 经 R86(0Ω) 回到 `GPIOA_2`。**GPIOA_2 = 完整 PCIe↔USB3.0 运行时切换脚，硬件无需改动**：LOW=SW1=USB3.0，HIGH=SW2=PCIe。详见 §8.1。
2. ✅ **摄像头未使用** → DTS 不写 `&csi`。
3. ✅ **PHY0_LED0/1 为 CFG→LED 硬件 strap**（上电采样配置，延时后作 RJ45 灯）→ DTS 无需配置。
4. ✅ **RGMII_RST# ──R50(0Ω)── PHY0_RSTN 为同一路复位** → 核心板拉低 `RGMII_RST#` 即可，底板不另配 GPIO。
5. ✅ **FPC5 = SPI 屏幕模块**，经 CN2 桥接：GPIOH_4=**SPI_B_MOSI**、GPIOH_5=**SPI_B_MISO**、GPIOH_7=**SPI_B_SS0**、GPIOH_6=**SPI_B_SCLK**、GPIOH_8=LCD_BL_EN；GPIOA_3/A4 = 屏的 SPI_RST/SPI_RS（普通GPIO）。
6. ✅ **GPIOH_8 经 Q15(MMBT3906, **PNP**) 控制 3.3V 背光导通** → **GPIO_ACTIVE_LOW**（拉低导通）。
7. ✅ **以太网 = RGMII 千兆（1000M），唯一网口**；FPC6 已删除，**不使用 RMII**。
8. ✅ **器件阻值以 `={Value}` 字段为准**，非型号编码（已在全文修正）。
9. ✅ **Q15 料号已改为 `MMBT3906 2A(RANGE:100-300)`（PNP）**，网表确认，Emitter→A_3V3 高边成立 → 背光 `GPIO_ACTIVE_LOW`。
10. ✅ **Q8 保持 `PMBS3904,215-JSM`（NPN）**，Emitter→GND 低边 → 运行灯 `GPIO_ACTIVE_HIGH`。**两颗粒号不同、极性相反。**
11. ✅ **FPC6 / CN6 已从网表删除**（元件表与网络中均无残留）。
12. ✅ **两颗 SHT40 均贴装**（U42@`TOUCH_I2C`/GPIOA_14-15、A_3V3；U45@`I2C_AO_S0`/AO 域、`VDDIO_AO18` 1.8V），**不同 I2C 控制器，同地址 0x44 合法共存** → §7.3
9. ✅ **IR 接收头 = U38(IRM-V838M3-C/TR1) → `IR_IN` → 核心板 `GPIOAO_5`**（复用名 `IR_REMOTE_IN`/`PWMAO_D`）。
10. ✅ **SPI_B 走 GPIOH 组**：MOSI=GPIOH_4、MISO=GPIOH_5、CS=GPIOH_7、SCLK=GPIOH_6；**GPIOA_3/4 不参与 SPI_B**（当普通 GPIO 用）。
11. ✅ **触控 I2C = `TOUCH_I2C_SDA/SCL` → CN2-62/64 → `GPIOA_14`(`WORLD_SYNC`/`I2C_EE_M3_SDA`) / `GPIOA_15`(`IR_REMOTE_IN`/`I2C_EE_M3_SCL`)**，线上挂 **U42 SHT40（0x44）** + FPC3 触控座（未贴）。
12. ⚠ ~~第二颗 SHT40 二选一~~ → **已作废**：网表终版为 **U42/U45 两颗都贴装**（`bom=yes`），分挂`I2C_EE_M3` 与 `I2C_AO_S0` 两个不同 I2C 控制器，同地址 0x44 合法 → §7.3
13. ✅ **A311D 只有 1 个 SDIO 控制器**（`&sd_emmc_a`），另两个是 `sd_emmc_b`(SD卡)/`sd_emmc_c`(eMMC)。AP6256 固定占 `&sd_emmc_a`，无第二个 SDIO 可选。
14. ✅ **SL6341D(U31) 是 USB3.0 Hub，不需要 A311D 控制**（独立器件，无 SoC GPIO 依赖）。
15. ✅ **MT9700 的 EN 改为电阻上拉常开**（R158 由 GPIOAO_11 改接 VCC5V），**GPIOAO_11 释放**；MT9700 无 I2C/寄存器 → **DTS 不写任何节点** → §10.1
16. ✅ **GPIOA_7 控 SL6341D 复位 —— 评估否决**：U31.pin31=`RSTN` 已有 C126+R95 硬件复位；Hub 无需运行时复位，驱动异常触发复位会导致已枚举 USB 设备全部掉线。GPIOA_7 保留。

## 14. 待确认项

**DTS 引脚归属与极性已全部确定，无剩余待确认项。**

> ⚠ **已作废的描述**：`VDDCPU_B_EN`(CN3-73) 经R6/R12 接 U4(RT9013-18GB) EN —— **该描述无效**。
> 网表实测 `VDDCPU_B_EN` 整条链路（R6=100kΩ、R12=0Ω、Q2(PMBT3904)、U4(RT9013-18GB)）
> **全部标记 `Add into BOM=no` / `Convert to PCB=no`，即未使用器件**。
> → `VDDCPU_B_EN` 是未使用网络，**DTS 不处理**。

### 已排除项
- ✅ `SPI_RST`/`SPI_RS` = GPIOA_3/GPIOA_4（**普通 GPIO，SoC 无 SPI 复用，仅统一命名**）→ §7.0
- ✅ `VDDIO_X` = **1.8V**（源自 `VDDIO_AO18`，GPIOX 组）；`ETH_VDDIO` = **3.3V**（**GPIOZ 组**，独立电压域）→ §7.0.1
- ✅ **SARADC 未使用**（`SARADC_CH0` CN3-51、`SARADC_CH3` CN3-57 均悬空）→ DTS 不写 adc-keys
- ✅ **RGMII / RMII 完全互斥**（`PRG_ETH_REG1[0]`，仅复位时采样）→ §7.0.2
- ✅ **A311D MAC 侧可设 RGMII TX 延迟**（`PRG_ETH_REG1[6:5]`，0/¼/½/¾ cycle）→ 用 `phy-mode` 而非直接写寄存器 → §7.0.3
- ✅ **`HW_VS`(CN3-53) 悬空**（官方参考原理图即如此）→ DTS 不处理
- ✅ **`SYS_LED` = 运行指示灯 LED4**：`GPIOAO_10` → R110(100Ω) → Q8(PMBS3904 **NPN**, Emitter→GND) → LED4；`GPIO_ACTIVE_HIGH` → §3.1
- ⚠ **`VDDCPU_B_EN`(CN3-73) 未使用**（R6/R12/Q2/U4 全部 bom=no）→ DTS 不处理
- ✅ **PMBS3904,215-JSM = NPN**（规格书实锤，SOT-23: 1=B/2=E/3=C），非 P-MOS → §3.1
- ✅ **Q15 = MMBT3906（PNP）**，网表误填 PMBS3904 是复制粘贴错误（用户核对）→ 背光 `GPIO_ACTIVE_LOW` → §7.1

### 全文未使用器件清单（`Add into BOM=no`，DTS 一律不引用）

| 位号 | 型号 | 备注 |
|------|------|------|
| U4 | RT9013-18GB | 1.8V LDO，与 U3 同料双料 |
| U30 | FSW3410YQFN18G/TR | USB3 控制器（U31=SL6341D 才是实际用的）|
| Q2 | PMBT3904 | `P_G` 支路 |
| Q1 | 2KJ7107DFN | `P_G` 支路 |
| SW5 | TSA020B3440A02 | ADC 键 |
| FPC3 各脚 | FPC30-T1T1-2010-A | 未使用 |
| Q13 / Q14 | MS3134 | I2C 电平转换（原摄像头 I2C_AO_M0 通路，现未使用）|
| R121 / R130 / R124 / R126 / R128 / R10 / R123 | — | 0Ω/22Ω 预留位 |
| ~~CN6~~ | ~~SM06B-GHS-TB~~ | **已删除**（FPC6 一并移除）|

### 本次重新导出核验新增器件（`bom=yes`，需引用）

| 位号 | 型号 | 用途 |
|------|------|------|
| **U45** | SHT40-CD1B-R3 | AO 域温湿度，I2C `I2C_AO_S0`，地址 0x44 |
| **C218** | CL05B104KB54PNC | U45 去耦（VDDIO_AO18/GND）|
| **Q15** | **MMBT3906 2A(RANGE:100-300)** | **PNP**，背光高边开关（料号已修正）|