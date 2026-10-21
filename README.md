# halo-a311d

Amlogic A311D —— **Halo 底板** + **荣品 PRO-A311D 核心板**，mainline 内核与设备树，基于 armbian/build 构建。

[![dtb-check](https://github.com/iorca/halo-a311d/actions/workflows/dtb-check.yml/badge.svg)](https://github.com/iorca/halo-a311d/actions/workflows/dtb-check.yml)
[![kernel-build](https://github.com/iorca/halo-a311d/actions/workflows/kernel.yml/badge.svg)](https://github.com/iorca/halo-a311d/actions/workflows/kernel.yml)

两条 CI 都跑在 GitHub 官方 runner，无需自托管：
- **dtb-check**（`ubuntu-24.04`）：只编 dtb，约 20~30 秒，DTS 语法快检
- **kernel-build**（`ubuntu-24.04-arm`）：armbian 完整构建，50~55 分钟（target=build）

---

## 状态速览（CI 实证，非推断）

| target | 分支 | 结果 | 证据 |
|---|---|---|---|
| `kernel` | main | ✅ | run `39462193272`，产物 `halo-a311d-kernel` 71 MB，两个 dtb 齐全 |
| `uboot` | gxlimg | ✅ | run `39457685081`，`linux-u-boot-halo-a311d-current`（主线 u-boot v2026.04 重打包进厂商 FIP）|
| `firmware` | 两分支 | ✅ | run `39456750049`，164 MB |
| `build` | gxlimg | ✅ | run `39547492248`，Runtime 54:37，**1.68 GiB 镜像**，`boot.scr` 已含冷切换逻辑 |
| `rootfs` | — | — | 未单独跑；`build` 已含 rootfs 环节 |

⚠ **全部只在 CI 里验证过「编得出来 + 文件都在」，真机启动仍未验证。** 见文末已知限制。

### Release 发布：只认「可刷写镜像」

判据是**产物性质** —— 五个 target 里只有 `build` 会产出 `.img`，也只有它刷得进机器。
所以 Release 只在 `TARGET_KIND == build` 时发布，`kernel`/`uboot`/`rootfs`/`firmware`
出的都是 deb 或归档，不发布。

两种发版方式，**任选其一**：

**方式 A — 推 tag**（语义更正式，会新建 tag）
```bash
git checkout gxlimg-full-mainline-uboot
git tag -a v2026.10.21-mainline -m "发布说明"
git push origin v2026.10.21-mainline
```

**方式 B — 手动 dispatch**（不新建 tag，省一步）
在 Actions 页面 `kernel-build` → `Run workflow`：
- `target` 选 **build**
- `release` 选 `noble`
- `tag` 可留空（自动生成 `build-<日期>-<sha8>`），也可手填如 `v2026.10.21-mainline`

> 推 tag 时 `TARGET_KIND` 被强制为 `build`（`.github/workflows/kernel.yml:95`），
> 两种方式最终都会跑完整镜像并发布 `.img` + 两个 dtb + deb。
>
> 真兜底是脚本里的 `IMAGES` 空值检查：找不到镜像直接 `exit 1`，
> 不会发出一个「只有 dtb、没有可刷镜像」的 Release。

---

## 分支策略

| 分支 | u-boot 来源 | 说明 |
|---|---|---|
| `main` | LibreELEC khadas-vim3 FIP（厂商原版 u-boot） | 稳定路线 |
| `gxlimg-full-mainline-uboot` | `fip-blob/` 里的厂商完整 FIP + **gxlimg 重打包主线 u-boot** | 主线 u-boot 路线 |

只有 `config/boards/halo-a311d.conf` 和 `scripts/deploy-to-build.sh` 在两个分支上**内容不同**
（gxlimg 版多了 fip-blob 注入段、hook 用 `gxlimg_repack_fip_with_new_uboot`）。
其余文件两边一致 —— **同步时别整文件跨分支拷**，会互相覆盖独有段。

---

## 快速开始

```bash
git clone --depth 1 https://github.com/armbian/build.git
./scripts/deploy-to-build.sh ../build      # 注入本仓库板级文件
cd ../build
./compile.sh kernel BOARD=halo-a311d BRANCH=current
```

产物：`output/debs/linux-{image,dtb,headers}-current-meson64_*.deb`

CI 里手动触发（workflow_dispatch）的 `target` 只有这五个 —— armbian **没有 `image` 这个
target**（传错会 `Unknown argument image` + exit 43）：

| target | 说明 |
|---|---|
| `kernel`（默认） | 只编内核 deb |
| `build` | 内核 + rootfs + **完整镜像**（推 tag 时强制走这个）|
| `uboot` | 只编 u-boot |
| `rootfs` | 只编 rootfs（需 `release`）|
| `firmware` | 只编固件包 |

---

## 仓库结构

```
dt/meson-halo-a311d.dts          USB3.0 设备树（默认）
dt/meson-halo-a311d-pcie.dts     PCIe 设备树
config/boards/halo-a311d.conf    armbian 板级配置（两分支不同）
config/sources/families/meson-g12b.conf
                 覆盖 uboot_custom_postprocess，把本板接进 FIP 组装
fip-blob/halo-a311d/             厂商完整 FIP（gxlimg 分支用；main 不需要）
boot/boot-meson64.cmd            ⭐ armbian boot.cmd 的 fork，含冷切换逻辑
boot/althaea-mode.hush            冷切换脚本（可读参考，u-boot 不会自动 source）
scripts/deploy-to-build.sh        注入到 userpatches（两分支不同）
scripts/customize-image.sh        chroot 内执行，把 overlay 文件放进镜像
.github/workflows/dtb-check.yml   CI：dtb 语法快检
.github/workflows/kernel.yml      CI：ARM64 armbian 构建
docs/                             文档、厂商 DTS、VIM3 参考、电源树
work/ netlist-dump/               过程性分析脚本与网表导出
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

**两个必须理解的 armbian 机制**

1. **`/userpatches` 被官方 `.gitignore` 排除** —— armbian 约定它是本地覆盖、不进版本库。
   所以板级文件由本仓库保管，CI 检出 armbian 后用 `deploy-to-build.sh` 注入。

2. **板级 dts 目录名必须严格等于 `KERNELPATCHDIR`**，否则 dts 被静默忽略：
   ```bash
   # config/sources/common.conf:126
   KERNELPATCHDIR="archive/${KERNEL_PATCH_ARCHIVE_BASE}-${KERNEL_MAJOR_MINOR}"
   ```
   `meson64_common.inc` 的 `case $BRANCH`：`current→6.18` `edge→7.3` `oldlts→6.12`
   → **BRANCH=current 必须注入 `userpatches/kernel/archive/meson64-6.18/dt/`**
   → 写死的症状是「编译 success、deb 也产出，但包里没有本板 dtb」，极难查。

---

## PCIe / USB3.0 冷切换

A311D 的 PCIe 与 USB3 共用同一个 combo PHY（`usb3_pcie_phy`）：

```dts
/* meson-g12-common.dtsi:164  */ &pcie { phys = <&usb3_pcie_phy PHY_TYPE_PCIE>; };
/* meson-g12-common.dtsi:2510 */ &usb  { phys = <&usb3_pcie_phy PHY_TYPE_USB3>; };
```

PHY 归属**编译期定死**（`#phy-cells = <1>`），运行期只改 SEL 只能换物理通路，
SoC 内部仍按 dtb 写死的那一侧枚举 → 失效。所以必须**冷切换：重启时选对应 dtb**。

### 硬件：R85 / R87 选贴，SEL 是 strap

```
GPIOA_2 ──┬── R86(0Ω)  ──→ U28.6 (FUSB340 SEL)
          ├── R87(4.7k) ──→ A_3V3   上拉   → 贴这个 = PCIe
          └── R85(4.7k) ──→ GND     下拉   → 贴这个 = USB3.0（默认）
```

**必须二选一，不能都不贴**（FUSB340 规格书：*"must not float"*）；两颗都贴则被分压成
1.65V，属未定义电平。

**SEL 由电阻决定，SoC 不许驱动** —— 两个 dts 变体都在 `&gpio`（periphs bank）下
定义了 `fusb340_sel_hog` hog，状态属性显式写 `input`：

```dts
&gpio {
    fusb340_sel_hog: fusb340_sel_hog {
        gpio-hog;                              /* 必需（bool） */
        gpios = <GPIOA_2 GPIO_ACTIVE_HIGH>;    /* 必需 */
        input;                                 /* 必须三选一：input/output-low/output-high */
        line-name = "FUSB340_SEL";
    };
};
```

SoC 一强驱（写 `output-*`）就把 strap 电平盖掉，读出来永远是自己的输出值。

⚠⚠ **两个容易踩的坑**（本仓库都踩过）：

1. **hog 必须是 gpio-controller 的子节点**。放在根节点下内核根本不会扫它
   （`drivers/gpio/gpiolib-of.c: of_gpiochip_scan_gpios()` 只遍历
   `dev_of_node(&chip->gpiodev->dev)` 的子节点）。
2. **状态属性必须显式写一个**。`input` / `output-low` / `output-high` 三选一，
   一个都不写时内核会打印
   `"no hogging state specified, bailing out"` 并**跳过该 hog** ——
   **不是"自动变成 input"**。

⚠ 另外注意：input hog 会让该线被内核标记为 REQUESTED，
**userspace 不能再 export 读写它**（不能 `echo` 到 `/sys/class/gpio/...`）。

### 软件链路（不是 extlinux）

```
boot/boot-meson64.cmd
  └→ userpatches/bootscripts/boot-meson64.cmd   （armbian 优先用这份覆盖自己的）
       └→ 镜像构建时由上游 partitioning.sh 编译成 /boot/boot.scr
            ├─ load armbianEnv.txt + env import -t
            ├─ 注入块：gpio read → setenv fdtfile
            └─ load ... dtb/${fdtfile}
```

**boot.scr 是谁编的**（上游 `lib/functions/image/partitioning.sh:511-527`）：

```bash
if [[ -f "${SDCARD}/boot/boot.cmd" ]]; then
    BOOTSCRIPT_OUTPUT=boot.scr        # 未设时的默认值
    mkimage -C none -A arm -T script -d "${SDCARD}/boot/boot.cmd" "${SDCARD}/boot/boot.scr"
fi
```

上游 `lib/functions/main/rootfs-image.sh:97-98` 的顺序是
`prepare_partitions`（编 boot.scr）→ `create_image_from_sdcard_rootfs`（rsync /boot 进镜像），
**先编后拷，顺序正确**。

> ⚠ 另有一条**设备侧**路径：`armbian-bsp-cli` 的 postinst
> （`lib/functions/bsp/armbian-bsp-cli-deb.sh`）也会用 mkimage 生成 boot.scr，
> 但只在 `BOOTSCRIPT_FORCE_UPDATE == yes || ! -f /boot/boot.cmd` 时才跑 ——
> 那是设备上首次装/升级 bsp-cli 用的，与镜像构建路径相互独立。

### ⚠ GPIO 必须写数字 51，符号名无效

```bash
gpio read althea_sel 51
```

`GPIOA_2` / `A_2` / `FUSB340_SEL` **三种都解析不了**，只会打印 `GPIO: 'x' not found`
然后静默兜底 USB3.0、PCIe 永远选不上。原因（u-boot 2026.04 源码）：

- `drivers/pinctrl/meson/pinctrl-meson.c:334` → `bank_name = priv->data->name` = `"periphs-banks"`
- `drivers/gpio/gpio-uclass.c:176` 用**前缀匹配**，`"GPIOA_2"` vs `"periphs-banks"` 不匹配
- 标签查找（`gpio-uclass.c:128`）只匹配已 request 的脚；`gpio-line-names` 需 `CONFIG_DM_GPIO_LOOKUP_LINE_NAME`

**51 的推导**：periphs banks 顺序 `Z(0-15) H(16-24) BOOT(25-40) C(41-48) A(49-64) X(65-84)`
（`pinctrl-meson-g12a.c:1205`，`num_pins=85`，`pin_base=EE_OFF=15`）→ GPIOA_2 偏移 `49+2=51`；
`gpio_base` 按探测顺序累加，periphs 节点（`meson-g12-common.dtsi:271`）早于 aobus（`:1759`）
→ base=0 → **51**。备选型 `66`（=51+EE_OFF，Linux 侧编号）。

依赖 `CONFIG_CMD_GPIO` + `CONFIG_CMD_GPIO_READ`（已在 board conf 的
`post_config_uboot_target__extra_configs_for_halo_a311d()` 里打开）。

上机在串口看这几行即可确认：
```
althea: SEL(gpio 51 = GPIOA_2) = 1
althea: SEL=HIGH -> PCIe
althea: fdtfile=amlogic/meson-halo-a311d-pcie.dtb
```

详见 [docs/冷切换使用说明.md](docs/冷切换使用说明.md)。

---

## DTS 编写要点与踩过的坑

### 1. 必须显式 include dt-bindings 头

```c
#include <dt-bindings/gpio/meson-g12a-gpio.h>
#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/leds/common.h>
#include <dt-bindings/input/linux-event-codes.h>
#include <dt-bindings/interrupt-controller/irq.h>
```

缺了会怎样：`GPIOAO_10` 未定义 → 预处理把 `>` 当比较运算符 → 报错指向 `GPIOAO_10` 那一列，
完全看不出真实原因。（VIM3 靠 `meson-khadas-vim3.dtsi` 间接引入，板级文件没这层依赖。）

### 2. LED 的 trigger 属性必须写 `linux,default-trigger`

⚠⚠ **本条曾写反过**（原文写的是"不能写 `linux,default-trigger`"），已更正。

`linux,` 前缀**不是** binding 文档的写法而已 —— 它就是内核实际读的属性名：

```dts
run_led {
    label = "run";
    gpios = <&gpio_ao GPIOAO_10 GPIO_ACTIVE_HIGH>;
    linux,default-trigger = "heartbeat";   /* ✅ 必须带 linux, 前缀 */
    default-state = "on";                  /* ✅ 不是 "state" */
};
```

源码依据（v6.18）：

| 属性 | 谁读 | 行号 |
|---|---|---|
| `linux,default-trigger` | `drivers/leds/led-class.c` | 504 |
| `default-state` | `drivers/leds/led-core.c` → `led_init_default_state_get()` | 607 |
| plain `default-trigger` | **无人读** | — |
| plain `state` | **无人读** | — |

- `drivers/leds/leds-of.c` 已在 6.18 **删除**（`https://github.com/torvalds/linux` 全树
  搜索 `drivers/leds/leds-of.c` 返回 404），gpio-leds 走的是 LED core 的
  `fwnode_property_read_string(init_data->fwnode, "linux,default-trigger", ...)`。
- 写成 plain `default-trigger` → 属性被**静默忽略** → 灯常亮不闪，且**编译期无任何报错**。
- 写 `state = "on"` 同样无效（真正读的是 `default-state`）。

> dtc 不报错 ≠ 内核会读。属性名写错属于"编译通过、运行不生效"，
> CI 的语法检查抓不到，只能靠对着内核源码核对。

### 3. 不要 include `<dt-bindings/regulator/fixed-regulator.h>`

该文件在内核中不存在。cpp 遇 fatal error 会中断，**后续全部报成假语法错**，行号对不上。

### 4. SPI 用 `&spicc1`，SS0 要单独列进 pinctrl

```dts
&spicc1 {
    pinctrl-0 = <&spicc1_pins>, <&spicc1_ss0_pins>;   /* 两个都要 */
    num-cs = <1>;
    cs-gpios = <&gpio GPIOH_6 GPIO_ACTIVE_LOW>;
};
```

mainline 只有 `spicc0`/`spicc1`/`spifc`，**没有 `spi_A`/`spi_B`**。
厂商命名对应：`SPI_B` → `spi1`(pinctrl group) / `spicc1`(控制器)；`I2C_EE_M3` → `i2c3`。

### 5. 本地编译命令

```bash
cpp -nostdinc -I <kernel>/arch/arm64/boot/dts/amlogic -I <kernel>/include \
    -undef -D__DTS__ -x assembler-with-cpp <file>.dts -o /tmp/out.dts
dtc -I dts -O dtb -o /tmp/out.dtb /tmp/out.dts
```

- 必须 `-I <kernel>/include`（dt-bindings 在这里，不在 `scripts/dtc/`）
- ⚠ `include/dt-bindings/input/linux-event-codes.h` 是指向 `../../uapi/...` 的**符号链接**
  → sparse checkout 必须同时拉 `include/uapi`，否则断链

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
| FUSB340 SEL | GPIOA_2 | LOW=USB3.0 / HIGH=PCIe（strap，不是输出）|
| PCIe PERST# | GPIOA_0 | `ACTIVE_LOW`（R88 4.7k 上拉 A_3V3）|
| PCIe PEWAKE | GPIOA_1 | R89 4.7k 上拉 |
| PCIe CLKREQ# | GPIOC_7 | `ACTIVE_LOW`（R90 4.7k 下拉）|
| U42 SHT40 | GPIOA_14/A15 | `&i2c3` ✅ 已启用 |

⚠ **U45 (第二颗 SHT40) 已从 DTS 移除**：网表（`netlist-dump/nl_parsed_full.json`）显示
`I2C_AO_S0_SCL` / `I2C_AO_S0_SDA` **各只有 1 个连接点**（就是 U45 自己）——
信号线单端悬空，既没接 SoC 的 AO I2C 引脚，也没有上拉电阻。
对比 U42 所在的 `TOUCH_I2C_SCL/SDA` 直连 CN2-64/62 → GPIOA_15/A14。
→ 这颗器件收不到 ACK，驱动永远探测不到它，写节点只是误导。

⚠ 同理，**`rtc@51` (hym8563) 也已移除**：本板 495 个元件里没有任何 RTC 芯片，
该节点是从厂商 BSP 抄来的，本板无对应硬件。

`&i2c_AO` 控制器本身保留（AO 域 I2C 引出到 CN3-69/71），但**不挂任何设备节点**。

### CPU 供电（照抄 VIM3，已核实引脚）

| 电源 | 核 | 控制器+通道 | 引脚 | pinctrl group |
|---|---|---|---|---|
| VDDCPU_A | A73 大核 | `&pwm_ab` **0** | **GPIOE_2** | `pwm_a_e_pins` |
| VDDCPU_B | A53 小核 | `&pwm_AO_cd` **1**(D) | **GPIOE_1** | `pwm_ao_d_e_pins` |

Amlogic PWM 两两配对（AB / CD / EF）；`pwms = <&pwm_AO_cd 1 1250 0>` 里的 `1` = D 通道。

---

## 以太网

RTL8211F，`phy-mode = "rgmii"`，`reg = <1>`：

```dts
&ethmac {
    phy-mode = "rgmii";
    pinctrl-0 = <&ethmac_rgmii_pins>;
    pinctrl-names = "default";
    phy-handle = <&phy_0>;
    tx_delay_ns = <2>;
    rx_internal_delay_ps = <2000>;
};
&phy_0 { reg = <1>; };
```

---

## CI 说明

### dtb-check（`ubuntu-24.04`）

```
1. Verify toolchain     dtc 预装则跳过，显式 command -v 校验
2. Sparse-clone dts    amlogic + include/dt-bindings + include/uapi，test -f 验符号链接
3. Compile DTBs         预检(SoC依赖/dts/头文件) → cpp → dtc
                        ✅ dtc 退出码 + 产物非空 + 过滤后 stderr 三层判据
```

### kernel-build（`ubuntu-24.04-arm`）

```
1. Install deps          只装 armbian 主机侧工具，交叉编译器交给 armbian toolchain
2. Cache armbian sources cache/sources
3. Clone armbian/build   幂等（cache 恢复后目录非空也能处理）
4. Inject board files    deploy-to-build.sh + 存在性校验
5. Build kernel          ./compile.sh <target> BOARD=halo-a311d BRANCH=current
6. Collect artifacts     ⭐ 按 target 硬校验必需产物，缺了 exit 1
7. Publish Release       ⭐ 仅 target=build（唯一产出可刷镜像的 target）；缺镜像则 exit 1
```

> 步骤 7 在 `kernel`/`uboot`/`rootfs`/`firmware` 时会 skipped —— 那几个 target
> 不产 `.img`，发的 Release 也没意义，不是失败。

另有 `cron '0 6 * * 1'` 每周一增量重建。

> **别被绿灯骗了。** CI 里凡是「检查产物/条件是否存在」的地方都必须配 `exit 1`；
> 只写 `::error::` 等于没检查（它只生成注解，不影响退出码）。这条踩过两次。

**耗时是最快的健康信号**：

| 耗时 | 含义 |
|---|---|
| ~1~2 min | dts 没进内核（KERNELPATCHDIR 路径错），或本就是 firmware 这种只打包的 target |
| ~50 min | 内核真在编译 |

---

## 已知限制

| 项 | 说明 |
|---|---|
| **真机未验证** | 全部只在 CI 编过，**没在板子上启动过** |
| `gpio read` 编号 | 51 是按「periphs 先探测」推的。上机若「贴了上拉却读到 LOW」，改 `althea_sel_num=66` 即可，不需重编 |
| 音频 | **完全不使用音频功能**。DTS 里 TDM/PDM/声卡相关节点（`&tdmif_a`、`&tdmin_a`、`&tdmout_a`、`&toddr_a~c` 等）全部不使能 |
| U45 SHT40 | 已从 DTS 移除 —— 网表显示其 I2C 线单端悬空（无 SoC 端、无上拉），本就探测不到 |

---

## 文档

| 文件 | 内容 |
|---|---|
| [docs/冷切换使用说明.md](docs/冷切换使用说明.md) | PCIe/USB3.0 冷切换：跳线、boot.cmd 链路、gpio 编号推导、排错 |
| [docs/DTS适配要求.md](docs/DTS适配要求.md) | DTS 适配要求与检查项 |
| [docs/GPIO_外设对应表.md](docs/GPIO_外设对应表.md) | GPIO 与外设对应关系 |
| [docs/GPIO_用于DTS适配.md](docs/GPIO_用于DTS适配.md) | DTS 用到的 GPIO 汇总 |
| [docs/MAIN_V0.3_核验报告.md](docs/MAIN_V0.3_核验报告.md) | 板级核验结果 |
| [docs/与厂家DTS比对清单.md](docs/与厂家DTS比对清单.md) | 与厂商 DTS 的差异清单 |
| [docs/厂商DTS差异清单.md](docs/厂商DTS差异清单.md) | 差异明细 |
| `docs/vendor_dts/` | 厂商 DTS 原文（`pro-a311d.dts` 等）|
| `docs/vim3/` | VIM3 参考 DTS |
| `docs/power_tree.svg` | 电源树图 |
