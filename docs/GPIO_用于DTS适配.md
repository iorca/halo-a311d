# MAIN_V0.3 — A311D GPIO ↔ 外设对应（DTS 适配用）

> SoC：Amlogic A311D
> 数据来源：Protel2 网表解析（GPIO 网络名 = A311D 引脚名，网络另一端 = 底板连接）
> 用途：写/改 device tree 时查 GPIO 归属与外设连接

## DTS 使用要点
- **AO 域**（`GPIOAO_*`）→ phandle 用 `&gpio_ao`
- **EE 域**（其余 `GPIOA/GPIOC/GPIOH/GPIOX/...`）→ phandle 用 `&gpio`
- pin 名沿用 Amlogic 方案，直接写 `GPIOA_0` / `GPIOH_8` / `GPIOX_19` / `GPIOAO_11`
- 标准写法：`gpios = <&gpio GPIOX_19 GPIO_ACTIVE_HIGH>;`（有效电平按外设定）
- 本表只给**硬件连接**；`GPIO_ACTIVE_*`、`input-enable` / `output-high` / `bias-pull-up` 等按外设需求在节点里填
- `GPIOA_5` 在本网表中未出现（未布线或保留，DTS 里不要引用）

---

## 一、EE 域 — `&gpio`

### GPIOA 组（→ 核心板 BTB）
| A311D GPIO | DTS 引用 | 底板连接 | 备注 |
|------------|----------|----------|------|
| GPIOA_0  | `&gpio GPIOA_0`  | CN230, R881, R922 | BTB，含电阻 |
| GPIOA_1  | `&gpio GPIOA_1`  | CN232, R892, R912 | BTB，含电阻 |
| GPIOA_2  | `&gpio GPIOA_2`  | CN236, R862, R872, R851, R1232 | BTB，含 0Ω/串联 |
| GPIOA_3  | `&gpio GPIOA_3`  | CN238, R1242, FPC53 | BTB + FPC |
| GPIOA_4  | `&gpio GPIOA_4`  | CN240, R1262, FPC54 | BTB + FPC |
| GPIOA_6  | `&gpio GPIOA_6`  | CN244 | BTB |
| GPIOA_7  | `&gpio GPIOA_7`  | CN246 | BTB |
| GPIOA_8  | `&gpio GPIOA_8`  | CN248 | BTB |
| GPIOA_9  | `&gpio GPIOA_9`  | CN250 | BTB |
| GPIOA_10 | `&gpio GPIOA_10` | CN252 | BTB |
| GPIOA_11 | `&gpio GPIOA_11` | CN254 | BTB |
| GPIOA_12 | `&gpio GPIOA_12` | CN256 | BTB |

### GPIOC 组（→ 核心板 BTB）
| A311D GPIO | DTS 引用 | 底板连接 | 备注 |
|------------|----------|----------|------|
| GPIOC_7  | `&gpio GPIOC_7`  | CN228, R902, R932 | BTB，含电阻 |

### GPIOH 组（→ 核心板 BTB + FPC）
| A311D GPIO | DTS 引用 | 底板连接 | 备注 |
|------------|----------|----------|------|
| GPIOH_4  | `&gpio GPIOH_4`  | CN210, FPC326, FPC55 | BTB + FPC |
| GPIOH_5  | `&gpio GPIOH_5`  | CN212, FPC328 | BTB + FPC |
| GPIOH_6  | `&gpio GPIOH_6`  | CN214, FPC327, FPC58 | BTB + FPC |
| GPIOH_7  | `&gpio GPIOH_7`  | CN216, FPC329, FPC56 | BTB + FPC |
| GPIOH_8  | `&gpio GPIOH_8`  | R102(3.4kΩ), CN218, R1282, R1651 | BTB，已带上拉 |

### GPIOX 组（→ 板载 IC / BTB）
| A311D GPIO | DTS 引用 | 底板连接 | 备注 |
|------------|----------|----------|------|
| GPIOX_6  | `&gpio GPIOX_6`  | CN340, U4012 | BTB + 板载 IC |
| GPIOX_7  | `&gpio GPIOX_7`  | CN342, U4013 | BTB + 板载 IC |
| GPIOX_19 | `&gpio GPIOX_19` | CN338, U406  | BTB + 板载 IC |

---

## 二、AO 域 — `&gpio_ao`

### GPIOAO 组（→ 板载 IC / BTB）
| A311D GPIO | DTS 引用 | 底板连接 | 备注 |
|------------|----------|----------|------|
| GPIOAO_6  | `&gpio_ao GPIOAO_6`  | CN345, U92 | BTB + 板载 IC |
| GPIOAO_11 | `&gpio_ao GPIOAO_11` | CN379, U84, R1581 | BTB + 板载 IC |

> AO 域 GPIO 在系统休眠时仍保持，适合做唤醒/电源相关管教；若这些脚用于 PMIC/电源使能，优先放 ao 域节点。

---

## 三、按底板连接类型归并（DTS 写节点时参考）

| 连接类型 | 位号 | 对应 GPIO（DTS） |
|----------|------|------------------|
| 核心板 BTB（CN2xx） | CN210/212/214/216/218/228/230/232/236/238/240/244/246/248/250/252/254/256/338/340/342/345/379 | `&gpio` GPIOH_4~8 / GPIOC_7 / GPIOA_0~12 / GPIOX_6/7/19；`&gpio_ao` GPIOAO_6/11 |
| 软排线（FPCxx） | FPC53/54/55/56/58/326/327/328/329 | `&gpio` GPIOA_3/4、GPIOH_4~7 |
| 板载 IC（Uxx） | U92, U84, U406, U4012, U4013 | `&gpio_ao` GPIOAO_6/11；`&gpio` GPIOX_6/7/19 |

---

## 四、待补（全工程多页网表导出后回填）
- **U92 / U84 / U406 / U4012 / U4013 型号与功能** → 决定这些 GPIO 挂什么 device node（如 expander / codec / 触控等）
- **CN2xx / FPCxx 连接器型号**
- 各 GPIO 的实际**功能方向**（输入/输出、中断、复用功能）——网表只给连接，不给功能，需对照原理图标注或询问

> 注：U92/U84/U406/U4012/U4013 的型号不在当前导出页（power 页）组件段内，需重连 立创EDA 导出全工程网表补齐，才能确定 DTS 里用什么 compatible / 挂哪个节点。
