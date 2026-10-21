# MAIN_V0.3 DTS — 与厂家 BSP 比对清单

> 用途：本板（MAIN_V0.3，自研底板）与厂家 BSP 底板（另一套硬件）合并 DTS 时逐项核对。
> 本板数据来源：全工程网表实测（495 元件 / 393 网络，2026-10-19 核验）。

## 使用方法

1. 从厂家 BSP 拿到 `.dtsi` / `.dts`
2. 按下表逐行对照，**重点看「本板引脚」vs「厂家引脚」是否一致**
3. 一致 → 直接沿用厂家节点
4. 不一致 → 二选一：
   - 改本板硬件（不现实，已定型）
   - **在本板 dtsi 里覆盖厂家节点**（在厂家 .dtsi 之后 include 本文）
5. 合并后逐项验证（见文末 checklist）

---

## 一、必须覆盖的节点（引脚不一致）

| 外设 | 本板引脚 | 风险 | 处理 |
|------|---------|------|------|
| **以太网 PHY** | U23 = **RTL8211F**，`reg=<1>`，`phy-mode="rgmii"` | 厂家 BSP 可能用 YT8531H 或不同地址 | 核对 PHY 地址 + phy-mode |
| **SPI_B** | CS=**GPIOH_7**、SCLK=**GPIOH_6**、MOSI=GPIOH_4、MISO=GPIOH_5 | 厂家 BSP 很可能用另一组脚 | **覆盖 `&spi_B` 的 cs-gpios + pinctrl** |
| **IR** | **GPIOAO_5** | 厂家可能用 GPIOX_* 或别的 AO 脚 | **覆盖 `&ir` 的 gpios** |
| **运行灯 LED4** | **GPIOAO_10** | 厂家板可能无此灯 | **新增/覆盖 `&leds` 节点** |
| **背光** | **GPIOH_8** | 厂家可能用 GPIOAO_* 做背光 | **确认 `lcd-backlight-gpios` 极性** |
| **SHT40 (U42)** | **GPIOA_14/A15** | 节点名/总线号可能不同 | 核对 I2C 控制器与 PHY 地址 |
| ~~SHT40 (U45)~~ | AO 域 I2C | **已移除**：网表显示其 I2C 线单端悬空 | 不用新增 |
| **FUSB340 SEL** | **GPIOA_2** | 厂家可能用于别的功能 | **核对 GPIOA_2 是否被厂商驱动占用** |

---

## 二、需核对的 PHY 地址与总线号

| 项 | 本板 | 核对方式 |
|----|------|---------|
| **YT8531H PHY 地址** | **1**（`3'b001`） | strap 实测：R78→A_3V3 / R79,R80→GND |
| **RTL8211F PHY 地址** | 同上（pin-to-pin，地址定义一致） | `dmesg` 应显示 `driver [RTL8211F]`，phy_id **0x001cc916** |
| **RGMII 延时** | **PCB 等长，2ns 全靠 PHY 内部延迟线** | 实测：TX 组散布 6.5mil(≈1ps)、RX 组 7.3mil(≈1ps)，clock-data 偏移仅 0.14ps vs 需求 2000ps |
| **phy-mode** | **`rgmii-id`** | 驱动用软件寄存器强制开 TX+RX 双延时；**禁用 `rgmii`（会关掉延时）** |
| ✅ 无需改硬件 | strap 状态无关 | `rgmii-id` 下驱动覆盖 strap，RXDLY 上下拉均不影响 |
| **SHT40 地址** | 0x44（固定） | U42 走 `&i2c3`；U45 已移除（信号线悬空） |
| **SDIO reg** | AP6256 在 bus 上 | 查 `ls /sys/bus/mmc/devices/` |
| **mmc alias** | mmc0=sd_emmc_c(eMMC)、mmc1=sd_emmc_b(SD)、mmc2=sd_emmc_a(SDIO) | 与厂家 BSP alias 对齐 |

---

## 三、可直接沿用厂家的部分

| 外设 | 说明 |
|------|------|
| **CPU / DDR / 时钟** | A311D 与 S922X pin-to-pin，SoC 级 DTS 无需改 |
| **MMC 控制器** | `sd_emmc_a/b/c` 由 SoC dtsi 定义，板级只加 pwrseq + PHY |
| **Ethernet MAC (`&gmac0`)** | 只需确认 `phy-mode` 与 PHY 地址 |
| **HDMI (`&hdmi_tx`)** | 主控在核心板，底板只做连接器 + CEC 转换 |
| **USB (`&dwc2` / `&xhci`)** | 走 FUSB340/Hub，属厂家 BSP 范畴 |

---

## 四、本板独有（厂家 BSP 通常没有）

| 项 | 说明 |
|----|------|
| **&leds（LED4 运行灯）** | GPIOAO_10，高电平亮 |
| ~~SHT40 U45~~ | 已从 DTS 移除 —— 网表显示 I2C 线单端悬空，探测不到 |
| **SHT40 U42** | EE 域 I2C + FPC3 触控座（触控座未贴）|
| **lcd-backlight-gpios** | GPIOH_8，PNP 高边，**ACTIVE_LOW** |
| **lcd-rst / lcd-rs** | GPIOA_3/A4，普通 GPIO |
| **FUSB340 SEL** | GPIOA_2（若厂家未用）|

---

## 五、极性对照表（最容易搞错，合并时重点核对）

| 信号 | 引脚 | 驱动器件 | 位置 | 极性 |
|------|------|---------|------|------|
| **运行灯 LED4** | GPIOAO_10 | Q8 = **NPN** | **低边** | **ACTIVE_HIGH**（拉高亮）|
| **LCD 背光** | GPIOH_8 | Q15 = **PNP** | **高边** | **ACTIVE_LOW**（拉低亮）|
| 红外 IR_IN | GPIOAO_5 | U38 输出 | — | ACTIVE_LOW |
| SPI 屏 RST/RS | GPIOA_3/A4 | 普通 GPIO | — | 查屏手册 |

> ⚠ **Q8(NPN低边) 与 Q15(PNP高边) 料号不同、极性相反**，别互相套用。

---

## 六、明确屏蔽项（不要在 DTS 里出现）

| 项 | 原因 |
|----|------|
| `&csi` / `&csi2` | 摄像头未使用 |
| `adc-keys` | SARADC_CH0/CH3 均悬空，SW5 未贴 |
| `gpio-keys`（底板） | 4 个按键全非 GPIO 直连，经 100Ω 送到 CN3 由核心板采样 |
| MT9700 任何节点 | EN 硬件上拉常开，无驱动，GPIOAO_11 已释放 |
| SL6341D 复位 GPIO | 已评估否决（U31 RSTN 有 C126+R95 硬件复位）|
| GPIOAO_11 | 已释放 |
| U4 / U30 / Q1 / Q2 / Q13 / Q14 / SW5 / CN6 / FPC6 | bom=no 或已删除 |

---

## 七、合并后验证 Checklist

```sh
# 1. 以太网 PHY 是否识别
dmesg | grep -iE "rtl8211f|yt8531|motorcomm|ethernet-phy|stmmac"
#   本板用 RTL8211F：期望 driver [RTL8211F]，phy_id 0x001cc916
#   （若换成 YT8531H 则为 0x0000011a）
#   ⚠ PHY 地址应为 1，若 dmesg 报 address 0 → 查 strap

# 2. PHY 地址是否正确
ls /sys/bus/mdio/devices/        # 应出现 ethernet-phy@N
mdio dump 0 0                    # 或 dmesg 打印 PHY ID

# 3. 链路速率是否到千兆
ethtool eth0 | grep -i speed     # 期望 1000Mb/s

# 4. SPI 屏是否点得亮
dmesg | grep -i spi              # spi_B 应正常 probe
#   屏 RST/RS 需示波器确认 GPIOA_3/A4 有波形

# 5. 背光极性
#   GPIOH_8 拉低 → 背光亮；拉高 → 灭

# 6. 运行灯
echo none > /sys/class/leds/run/brightness     # 灭
echo 1> /sys/class/leds/run/brightness         # 亮

# 7. SHT40 能读到（只应有 U42 一条；U45 已移除）
for i in /sys/bus/i2c/devices/*/; do
  [ -f "$i/name" ] && echo "$i: $(cat $i/name)"
done | grep -i sht
#   期望一条 SHT40 记录（U42 @ &i2c3）
#   ⚠ 若出现两条，说明 U45 节点仍在 DTS 里 —— 但 U45 信号线网表悬空，
#     正常情况下根本探测不到，出现即为异常

# 8. WiFi/BT
ifconfig wlan0                     # 或 nmcli dev
```

---

## 八、已知硬件注意点

### PCB 布局：R110（Q8 基极限流电阻）应靠近 Q8，不靠近核心板

链路：`CN3-37(SYS_LED) ── R110(100Ω) ── Q8.1(BASE)`，Q8.2(EMITTER)→GND，Q8.3(COLLECTOR)→LED4。

**结论：R110 紧贴 Q8 的 pin1(BASE) 放置，R110→BASE 走线 ≤ 几mm。**

理由（R110 在这里不是阻抗匹配电阻，而是**基极限流 + 噪声抑制**）：
1. 最敏感的节点是 **Q8 的 BE 结**（相当于一个大增益二极管），只需几 µA 耦合电流就能误导通；
2. 若 R110 放在连接器侧，则 R110→BASE 这段走线拾取的噪声**绕过 R110 直接灌进基极**，R110 的滤波作用完全失效；
3. R110 靠近 Q8 时，跨板线缆带来的噪声被 R110 分压（衰减 ~1000 倍）后才到基极；
4. R110→BASE 走线极短 → 天线面积最小 → 感应噪声最小。

> 注意区分：*"串联电阻靠驱动端"* 这条规则适用于**高速信号阻抗匹配**（如时钟/数据线）。
> 本例是低速 GPIO 控制，核心诉求是**抗干扰**，所以靠**负载端**。

**配套布局建议**
| 项 | 要求 |
|---|---|
| Q8.2(EMITTER) | 就近打 GND via，紧靠地平面 |
| R110→Q8.1 | 走线 ≤5mm，不与其他信号平行 |
| R108+LED4 回路 | 与 BASE 走线**远离**，避免耦合 |
| 跨板线缆侧 | 建议加 **10kΩ 下拉**至GND（见下）|

**⚠ 顺发现的设计缺口：`SYS_LED` 网络在下板侧没有任何上下拉电阻**

网表实测 `SYS_LED` 只有两个成员（`CN3.37` + `R110.1`），**无偏置电阻**。
风险：核心板 GPIO 处于 Hi-Z（boot 早期、线缆未插、复位期间）时，Q8 基极经长线缆悬空 → **运行灯可能随机闪烁/误亮**。

建议（二选一）：
- **方案 A**：下板在 CN3-37 处加 **10kΩ 下拉到 GND**（LED 灭态更确定）；
- **方案 B**：确认核心板 GPIOAO_10 侧已有下拉/上拉，则下板无需再加。

> 加 10k 下拉与 R110(100Ω) 分压：GPIO 驱动时 (3.3-0)/10k 侧仅 0.33mA，GPIO 轻松驱动；
> LED 电流由 R108(4.7k) 决定，约 (3.3-Vf)/4.7k ≈ 0.3mA，不受影响。

### 其他硬件注意点

1. **Q15 必须贴 MMBT3906（PNP）**，误贴 PMBS3904（NPN）→ 背光不亮（`V_BE` 需 4.0V > GPIO 上限 3.3V）
2. **R158 改接 VCC5V**（MT9700 EN 上拉），不再接 GPIOAO_11
3. **GPIOA_2 有 `TDMB_FS` 复用** → 若日后启用 TDM 音频会与 FUSB340 SEL 冲突
4. **R159=6.8kΩ** → USB4 OTG 限流 ≈ 1A
5. **PHY strap 电阻**决定 PHY 地址（实测 = 1）；延时由驱动接管，strap 无关
6. **R110=100Ω 时基极电流约 26mA**（(3.3-0.7)/100）。对GPIO 偏大（多数 SoC 额定 8mA，部分 26mA）。
   若实测 GPIO 驱动能力不足或边沿畸变，可考虑**加大到 220Ω~470Ω**（LED 电流仅 ~0.3mA，β 要求不高）。
7. **RGMII 延时不要试图用 PCB 走线补偿**：实测两组均等长（散布≈1ps），而 2ns 需约13000mil 走线。
   正确做法是 `phy-mode="rgmii-id"`，由 RTL8211F 内部延迟线提供 2ns。