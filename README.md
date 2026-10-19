# halo-a311d

Amlogic A311D 开发板 —— MAIN_V0.3 底板 + W400 核心板，Armbian 内核与设备树。

## 仓库结构

```
dt/meson-halo-a311d.dts         USB3.0 模式设备树（默认）
dt/meson-halo-a311d-pcie.dts    PCIe 模式设备树
config/boards/halo-a311d.conf   armbian 板级配置
config/sources/families/meson-g12b.conf
                               u-boot FIP 组装覆盖（覆盖 uboot_custom_postprocess）
fip/halo-a311d/                 FIP 二进制（bl2/bl30/bl31/acs 等，**勿手改**）
boot/althaea-mode.hush          U-Boot 模式选择脚本（冷切换）
scripts/deploy-to-build.sh      注入到 armbian-build 的 userpatches
.github/workflows/build.yml     CI：dtb 语法检查 + ARM64 内核编译
```

## PCIe / USB3.0 冷切换

A311D 的 PCIe 与 USB3 共用 combo PHY（`usb3_pcie_phy`），DTS 编译期即绑定，
运行期改 GPIO 无法同步 SoC 内部 → 采用**冷切换**。

硬件跳线（R85 / R87 二选一）：

| 贴装 | SEL 电平 | 模式 | DTB |
|------|---------|------|-----|
| R85（4.7k→GND，默认） | LOW | USB3.0 | `meson-halo-a311d.dtb` |
| R87（4.7k→A_3V3） | HIGH | PCIe | `meson-halo-a311d-pcie.dtb` |

> ⚠ **不能两颗都拆** —— FUSB340 规格书：`control inputs must not float`。
> 也不能两颗都贴（3.3V 分压成 1.65V，未定义电平）。

## 本地编译

```bash
git clone https://github.com/armbian/build.git
./scripts/deploy-to-build.sh ../build
cd ../build
./compile.sh kernel BOARD=halo-a311d BRANCH=current
```

## CI

- `dtb` job：x86 runner，几分钟，只验 DTS 语法 + 产 dtb
- `kernel` job：需 ARM64 runner（`[self-hosted, ARM64]`），编完整内核

## DTS 编译注意（踩过的坑）

1. 必须显式 include：
   ```c
   #include <dt-bindings/gpio/meson-g12a-gpio.h>
   #include <dt-bindings/leds/common.h>
   #include <dt-bindings/input/linux-event-codes.h>
   ```
   缺了则 `GPIOAO_10` 未定义，`>` 被 cpp 当比较运算符 → 语法错。
2. 属性名写 `default-trigger`，**不是** `linux,default-trigger`。
3. 不要 include `<dt-bindings/regulator/fixed-regulator.h>`（不存在，会让 cpp fatal 中断）。
4. SPI 用 `&spicc1`，pinctrl 必须同时列 `spicc1_pins` 和 `spicc1_ss0_pins`。
5. 编译命令必须带 `-I scripts/dtc/include-prefixes`。

## 关键引脚（网表实测）

| 功能 | 引脚 | 极性 |
|------|------|------|
| 运行灯 LED4 | GPIOAO_10 | ACTIVE_HIGH（Q8 NPN 低边）|
| 背光 | GPIOH_8 | ACTIVE_LOW（Q15 PNP 高边）|
| SPI 屏 CS | GPIOH_6 | ACTIVE_LOW |
| SPI 屏 RST/RS | GPIOA_3 / GPIOA_4 | 普通 GPIO |
| 红外 | GPIOAO_5 | ACTIVE_LOW |
| FUSB340 SEL | GPIOA_2 | LOW=USB3.0 / HIGH=PCIe |
| 以太网 PHY | RTL8211F, `reg=<1>` | `phy-mode="rgmii"` + `tx-delay-ns=2` + `rx-internal-delay-ps=2000` |
