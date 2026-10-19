# halo-a311d

Amlogic A311D 开发板 —— MAIN_V0.3 底板 + W400 核心板，mainline 内核与设备树。

[![dtb-check](https://github.com/iorca/halo-a311d/actions/workflows/dtb-check.yml/badge.svg)](https://github.com/iorca/halo-a311d/actions/workflows/dtb-check.yml)
[![kernel-build](https://github.com/iorca/halo-a311d/actions/workflows/kernel.yml/badge.svg)](https://github.com/iorca/halo-a311d/actions/workflows/kernel.yml)

两条 CI 均在GitHub 官方 runner 上运行，无需自托管：
- **dtb-check**（`ubuntu-24.04`）：只编 dtb，几十秒到 4 分钟，用于 DTS 语法快检
- **kernel-build**（`ubuntu-24.04-arm`）：完整 Armbian 内核 deb，约 50 分钟

---

## 快速开始

```bash
# 1. 克隆 armbian/build
git clone --depth 1 https://github.com/armbian/build.git

# 2. 注入本仓库的板级文件
./scripts/deploy-to-build.sh ../build

# 3. 编译内核
cd ../build
./compile.sh kernel BOARD=halo-a311d BRANCH=current
```

产物：`output/debs/linux-{image,dtb,headers}-current-meson64_*.deb`

---

## 仓库结构

```
dt/meson-halo-a311d.dts         USB3.0 模式设备树（默认）
dt/meson-halo-a311d-pcie.dts    PCIe 模式设备树
config/boards/halo-a311d.conf    armbian 板级配置
config/sources/families/meson-g12b.conf
                u-boot FIP 组装覆盖（重定义 uboot_custom_postprocess）
fip/halo-a311d/                  FIP 二进制 20 文件 2.8MB（**勿手改**）
boot/althaea-mode.hush           U-Boot 模式选择脚本（冷切换）
scripts/deploy-to-build.sh       注入到 armbian-build 的 userpatches
.github/workflows/dtb-check.yml  CI：dtb 语法快检
.github/workflows/kernel.yml     CI：ARM64 完整内核编译
docs/                            文档、厂商 DTS、VIM3 参考、规格书渲染
work/                            分析脚本（网表解析、dts 生成等过程文件）
netlist-dump/                    网表原始导出
```

---

## 板级配置

| 项 | 值 |
|---|---|
| BOARD | `halo-a311d` |
| BOARDFAMILY | `meson-g12b` |
| BOOTCONFIG | `khadas-vim3_defconfig`（同 SoC 复用）|
| SERIALCON | `ttyAML0`（UART_AO）|
| BOOT_FDT_FILE | `amlogic/meson-halo-a311d.dtb` |
| FIP_TREE_HALO_A311D | `${SRC}/fip/halo-a311d` |

**两个必须理解的 armbian 机制**

1. **`/userpatches` 被官方 `.gitignore` 排除**（第 19 行）——armbian 约定该目录是本地覆盖、不进版本库。
   所以本仓库独立保存板级文件，CI 检出 armbian 后由 `deploy-to-build.sh` 注入。

2. **板级 dts 目录名必须严格等于 `KERNELPATCHDIR`**，否则 dts 被静默忽略：
   ```bash
   # config/sources/common.conf:126
   KERNELPATCHDIR="archive/${KERNEL_PATCH_ARCHIVE_BASE}-${KERNEL_MAJOR_MINOR}"
   ```
   `meson64_common.inc` 的 `case $BRANCH`：`current→6.18` `edge→7.3` `oldlts→6.12`
   → **BRANCH=current 必须注入 `userpatches/kernel/archive/meson64-6.18/dt/`**
   → 写错的话症状是「编译 success、deb 产出，但包里没有本板 dtb」，最难查。
   → CI 已加 `dpkg-deb -c linux-dtb-*.deb | grep halo` 自动校验。

---

## PCIe / USB3.0 冷切换

A311D 的 PCIe 与 USB3 共用同一个 combo PHY（`usb3_pcie_phy`, phy@46000）：

```dts
/* meson-g12-common.dtsi:164  */&pcie { phys = <&usb3_pcie_phy PHY_TYPE_PCIE>; };
/* meson-g12-common.dtsi:2510 */&usb  { phys = <&usb3_pcie_phy PHY_TYPE_USB3>; };
```

PHY 的`#phy-cells = <1>`，调用方用 `PHY_TYPE_PCIE` / `PHY_TYPE_USB3` 区分模式。
**DTS 是编译期静态描述**，PHY 归属编译时定死；运行中改 FUSB340 的 SEL
只能改变物理通断，SoC 内部仍按 dtb 写死的一侧枚举设备 → 两侧不一致，失效。

→ 采用**冷切换**：U-Boot 阶段按跳线电平选一份静态匹配的 dtb，每次全新 probe。

### 硬件跳线（R85 / R87 二选一）

```
GPIOA_2 ──┬── R86(0Ω) ──→ U28.6 (FUSB340 SEL)
          ├── R87(4.7k) ──→ A_3V3    上拉
          ├── R85(4.7k) ──→ GND      下拉
          └── R123(22Ω) ──→ FPC3.22
```

| 贴装 | SEL 上电电平 | 模式 | DTB |
|------|-------------|------|-----|
| **R85**（下拉，默认） | LOW | USB3.0 | `meson-halo-a311d.dtb` |
| **R87**（上拉） | HIGH | PCIe | `meson-halo-a311d-pcie.dtb` |

>⚠ **不能两颗都拆** —— FUSB340 规格书 Recommended Operating Conditions Note 3：
> *"The control inputs must be held HIGH or LOW; **they must not float**."*
> 也不能两颗都贴（3.3V 被 4.7k//4.7k 分压成 1.65V，属未定义电平）。

### U-Boot 模式选择

`boot/althaea-mode.hush`：

```bash
gpio read althea_sel FUSB340_SEL
if test "${althea_sel}" = "1"; then
    setenv fdt /boot/meson-halo-a311d-pcie.dtb
else
    setenv fdt /boot/meson-halo-a311d.dtb
fi
```

在 `bootm` 之前 `source /boot/althaea-mode.hush`。

> ⚠ `gpio read` 需U-Boot 开启 `CONFIG_CMD_GPIO_READ`。
> `gpio status <pin>` **只打印不设环境变量**，脚本里不可用。
> U-Boot 无 `MESON_GPIO_A_0` 之类编译期常量，GPIO 号运行时从 `gpio-ranges` 算出，
> 所以**不能用固定编号**，须用名字（gpio-hog 的 `line-name`）或 bank 写法 `A_2`。

详见 [docs/冷切换使用说明.md](docs/冷切换使用说明.md)。

---

## DTS 编写要点与踩过的坑

### 1. 必须显式 include dt-bindings 头

```c
#include <dt-bindings/gpio/meson-g12a-gpio.h>   /* GPIOAO_10 等常量 */
#include <dt-bindings/gpio/gpio.h>              /* GPIO_ACTIVE_HIGH/LOW */
#include <dt-bindings/leds/common.h>            /* default-trigger 等 */
#include <dt-bindings/input/linux-event-codes.h>
#include <dt-bindings/interrupt-controller/irq.h>
```

**缺了会怎样**：`GPIOAO_10` 未定义 → 预处理时 `>` 被当成比较运算符 →
报错指向 `GPIOAO_10` 那一列，错误信息完全看不出真实原因。
（VIM3 靠 `meson-khadas-vim3.dtsi` 间接引入，板级文件没这层依赖。）

### 2. `default-trigger` 不能写 `linux,default-trigger`

`linux,` 前缀是内核 binding 文档的写法，dtc 不认，直接语法错。

### 3. 不要 include `<dt-bindings/regulator/fixed-regulator.h>`

该文件在内核中不存在。cpp 遇 fatal error 会中断，**后续全部报成假语法错**，行号完全对不上。

### 4. SPI 用 `&spicc1`，且 SS0 要单独列进 pinctrl

```
meson-g12-common.dtsi:1058  spicc1_pins      = groups "spi1_mosi","spi1_miso","spi1_clk"
meson-g12-common.dtsi:1070  spicc1_ss0_pins = group  "spi1_ss0"
```

```dts
&spicc1 {
    pinctrl-0 = <&spicc1_pins>, <&spicc1_ss0_pins>;   /* 两个都要 */
    num-cs = <1>;
    cs-gpios = <&gpio GPIOH_6 GPIO_ACTIVE_LOW>;       /* SPI_B_SS0 */
};
```

mainline 只有 `spicc0`(spi@13000)/`spicc1`(spi@15000)/`spifc`，**没有 `spi_A`/`spi_B`**。
厂商命名 → mainline 的对应：`SPI_B` → `spi1`（pinctrl group）/ `spicc1`（控制器）；
`I2C_EE_M3` → `i2c3`。交叉核对时两套名字都要搜。

### 5. 编译命令

```bash
cpp -nostdinc \
    -I <kernel>/arch/arm64/boot/dts/amlogic \
    -I <kernel>/include \
    -undef -D__DTS__ -x assembler-with-cpp \
    <file>.dts -o /tmp/out.dts
dtc -I dts -O dtb -o /tmp/out.dtb /tmp/out.dts
```

- **必须 `-I <kernel>/include`**（dt-bindings 常量在这里，不在 `scripts/dtc/`）
- ⚠ `include/dt-bindings/input/linux-event-codes.h` 是指向
  `../../uapi/linux/input-event-codes.h` 的**符号链接** → 用 sparse checkout 时
  **必须同时拉 `include/uapi`**，否则断链，`[ -f ]` 返回 false 误报"文件缺失"

---

## 关键引脚（网表实测）

| 功能 | 引脚 | 极性 / 备注 |
|---|---|---|
| 运行灯 LED4 | GPIOAO_10 | `ACTIVE_HIGH`（Q8 NPN 低边 + R110 100Ω）|
| 红外接收 | GPIOAO_5 | `ACTIVE_LOW`（U38 IRM-V838M3）|
| SPI 屏 MOSI/MISO | GPIOH_4 / GPIOH_5 | 硬件 SPI1 |
| SPI 屏 CS (SS0) | **GPIOH_6** | `ACTIVE_LOW` |
| SPI 屏 SCLK | **GPIOH_7** | ⚠ 与 CS 别弄反 |
| 屏 RST / RS | GPIOA_3 / GPIOA_4 | 普通 GPIO |
| 屏背光 EN | GPIOH_8 | `ACTIVE_LOW`（Q15 MMBT3906 PNP 高边）|
| FUSB340 SEL | GPIOA_2 | LOW=USB3.0 / HIGH=PCIe |
| PCIe PERST# | GPIOA_0 | `ACTIVE_LOW`（R88 4.7k 上拉 A_3V3）|
| PCIe PEWAKE | GPIOA_1 | R89 4.7k 上拉 |
| PCIe CLKREQ# | GPIOC_7 | `ACTIVE_LOW`（R90 4.7k 下拉）|
| U42 SHT40 | GPIOA_14/A15 | `&i2c3`，`i2c3_sda_a_pins`/`i2c3_sck_a_pins` |
| U45 SHT40 | I2C_AO | `&i2c_AO`，1.8V 域 |

两颗 SHT40 同地址 0x44但挂**两个独立 I2C 控制器**，合法共存。
切勿挂同一 `&i2c`（地址冲突 → 总线锁死）。

### CPU 供电（照抄 VIM3，已核实引脚）

| 电源 | 核 | 控制器+通道 | 引脚 | pinmux group |
|---|---|---|---|---|
| VDDCPU_A | A73 大核 | `&pwm_ab` **0** | **GPIOE_2** | `pwm_a_e_pins` |
| VDDCPU_B | A53 小核 | `&pwm_AO_cd` **1**(D) | **GPIOE_1** | `pwm_ao_d_e_pins` |

Amlogic PWM 两两配对（AB / CD / EF）。`pwms = <&pwm_AO_cd 1 1250 0>` 里的 `1` = 选该控制器的 D 通道。
A311D 规格书 Table 3-10 确认 `GPIOE_1 Func3 = PWMAO_D`、`GPIOE_2 = PWMAO_A`。

> ⚠ `VDDCPU_B_EN` / FUSB340 的 `TEST_N` 类信号：厂商 DTS 与 VIM3 都**没有**实现
> （VIM3 留了 `/* FIXME: actually controlled by VDDCPU_B_EN */`）。
> 本板网表里相关链路也全部 `bom=no` 未使用 → DTS 无需声明。

---

## 以太网

RTL8211F，`phy-mode = "rgmii"`，`reg = <1>`：

```dts
&ethmac {
    phy-mode = "rgmii";
    pinctrl-0 = <&ethmac_rgmii_pins>;
    pinctrl-names = "default";
    phy-handle = <&phy_0>;
    /* RGMII 内部延迟（PHY 侧加 2ns TX / 2ns RX）*/
    tx_delay_ns = <2>;
    rx_internal_delay_ps = <2000>;
};

&phy_0 { reg = <1>; };
```

---

## CI 说明

### dtb-check（`ubuntu-24.04`）

```
1. Verify toolchain        dtc 预装则跳过安装，显式 command -v 校验
2. Sparse-clone kernel dts --filter=blob:none --sparse
                           取 arch/arm64/boot/dts/amlogic + include/dt-bindings + include/uapi
                           + test -f 验证符号链接有效性
3. Compile DTBs            预检(SoC依赖/板级dts/逐个头文件) → cpp → dtc
                           过滤上游既有警告
```

### kernel-build（`ubuntu-24.04-arm`）

```
1. Install deps只装 armbian 主机侧工具，交叉编译器交给 armbian toolchain
2. Cache armbian sources  cache/sources（约 10GB，不全缓存）
3. Clone armbian/build    幂等：cache 恢复后目录非空也能处理
4. Inject board files     deploy-to-build.sh + 4 项存在性校验
5. Build kernel           ./compile.sh kernel BOARD=halo-a311d BRANCH=current
6. Collect artifacts      收集 dtb + deb，并 dpkg-deb -c 校验 dtb 真的在包里
```

手动触发可选参数：

| 参数 | 值 | 说明 |
|---|---|---|
| `target` | `kernel` | 只编内核（默认，约 50 min）|
| `target` | `image` | 完整系统镜像（慢，30~60 min）|

另有 `schedule: cron '0 6* * 1'` 每周增量重建。

**编译耗时是判断 dts 是否被采用的最快信号**：

| 耗时 | 含义 |
|---|---|
| ~1m45s | ⚠ dts 没进内核（KERNELPATCHDIR 路径错）|
| ~50 min | ✅ dts 真在编译 |

---

## 已知限制

| 项 | 说明 |
|---|---|
| **真机未验证** | dtb 已进包并在 CI 编译通过，但**未在板子上实际启动过** |
| `target=image` | 未验证 |
| U-Boot 模式切换 | `althaea-mode.hush` 未实机验证，需 `CONFIG_CMD_GPIO_READ` |
| 音频 | 网表只有 AL_CH/AR_CH 模拟通道，无 codec/功放 → 不配置声卡 |
| 双 SHT40 | 两个控制器各一个，同地址；U45 在 1.8V 域，实测 I2C 波形需确认 |

---

## 文档

| 文件 | 内容 |
|---|---|
| [docs/冷切换使用说明.md](docs/冷切换使用说明.md) | PCIe/USB3.0 冷切换完整步骤、跳线、常见问题 |
| [docs/DTS适配要求.md](docs/DTS适配要求.md) | DTS 适配要求与检查项 |
| [docs/GPIO_外设对应表.md](docs/GPIO_外设对应表.md) | GPIO 与外设对应关系 |
| [docs/GPIO_用于DTS适配.md](docs/GPIO_用于DTS适配.md) | DTS 用到的 GPIO 汇总 |
| [docs/MAIN_V0.3_核验报告.md](docs/MAIN_V0.3_核验报告.md) | 板级核验结果 |
| [docs/与厂家DTS比对清单.md](docs/与厂家DTS比对清单.md) | 与厂商 DTS 的差异清单 |
| [docs/厂商DTS差异清单.md](docs/厂商DTS差异清单.md) | 差异明细 |
| `docs/vendor_dts/` | 厂商 DTS 原文（`pro-a311d.dts` 等）|
| `docs/vim3/` | VIM3 参考 DTS |
| `docs/power_tree.svg` | 电源树图 |
