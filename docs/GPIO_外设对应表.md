# MAIN_V0.3 — A311D GPIO 与外设对应关系表

> 数据来源：Protel2 网表解析（`netlist_parsed.json`，当前导出页范围为 power 页，组件型号段不含 BTB/FPC/部分 IC，仅含位号与网络连接）
> SoC：Amlogic A311D（核心板经 BTB 连接器接入，本页即 BTB 连接器页）
> 说明：网络名 = A311D GPIO 引脚名；网络另一端 = 底板侧连接元件

## 分类约定
- **CN2xx** = 核心板 BTB 连接器引脚（连 A311D 核心板）
- **FPCxx** = 软排线连接器（连子板：屏/触摸/摄像头等）
- **Uxx** = 底板板载 IC（挂在 GPIO 上的外设，型号待全量导出确认）
- **Rxx** = 电阻（上拉 / 串联 / 0Ω）

---

## 1. GPIOA 组（→ 核心板 BTB）

| A311D GPIO | 网络 | 底板连接元件 | 类型 |
|------------|------|--------------|------|
| GPIOA_0  | GPIOA_0  | CN230, R881, R922 | 核心板 BTB |
| GPIOA_1  | GPIOA_1  | CN232, R892, R912 | 核心板 BTB |
| GPIOA_2  | GPIOA_2  | CN236, R862, R872, R851, R1232 | 核心板 BTB（含 0Ω/串联） |
| GPIOA_3  | GPIOA_3  | CN238, R1242, FPC53 | 核心板 BTB + FPC |
| GPIOA_4  | GPIOA_4  | CN240, R1262, FPC54 | 核心板 BTB + FPC |
| GPIOA_6  | GPIOA_6  | CN244 | 核心板 BTB |
| GPIOA_7  | GPIOA_7  | CN246 | 核心板 BTB |
| GPIOA_8  | GPIOA_8  | CN248 | 核心板 BTB |
| GPIOA_9  | GPIOA_9  | CN250 | 核心板 BTB |
| GPIOA_10 | GPIOA_10 | CN252 | 核心板 BTB |
| GPIOA_11 | GPIOA_11 | CN254 | 核心板 BTB |
| GPIOA_12 | GPIOA_12 | CN256 | 核心板 BTB |

> GPIOA_5 在本网表中未出现（可能未布线或保留）。

## 2. GPIOC 组

| A311D GPIO | 网络 | 底板连接元件 | 类型 |
|------------|------|--------------|------|
| GPIOC_7  | GPIOC_7 | CN228, R902, R932 | 核心板 BTB |

## 3. GPIOH 组（→ 核心板 BTB + FPC）

| A311D GPIO | 网络 | 底板连接元件 | 类型 |
|------------|------|--------------|------|
| GPIOH_4  | GPIOH_4 | CN210, FPC326, FPC55 | 核心板 BTB + FPC |
| GPIOH_5  | GPIOH_5 | CN212, FPC328 | 核心板 BTB + FPC |
| GPIOH_6  | GPIOH_6 | CN214, FPC327, FPC58 | 核心板 BTB + FPC |
| GPIOH_7  | GPIOH_7 | CN216, FPC329, FPC56 | 核心板 BTB + FPC |
| GPIOH_8  | GPIOH_8 | R102(3.4kΩ), CN218, R1282, R1651 | 核心板 BTB + 上拉 |

## 4. GPIOAO 组（→ 板载 IC）

| A311D GPIO | 网络 | 底板连接元件 | 类型 |
|------------|------|--------------|------|
| GPIOAO_6  | GPIOAO_6  | CN345, **U92** | 核心板 BTB + 板载 IC |
| GPIOAO_11 | GPIOAO_11 | CN379, **U84**, R1581 | 核心板 BTB + 板载 IC |

## 5. GPIOX 组（→ 板载 IC）

| A311D GPIO | 网络 | 底板连接元件 | 类型 |
|------------|------|--------------|------|
| GPIOX_6  | GPIOX_6  | CN340, **U4012** | 核心板 BTB + 板载 IC |
| GPIOX_7  | GPIOX_7  | CN342, **U4013** | 核心板 BTB + 板载 IC |
| GPIOX_19 | GPIOX_19 | CN338, **U406**  | 核心板 BTB + 板载 IC |

---

## 汇总（按底板连接类型归并）

| 连接类型 | 位号 | 对应 GPIO |
|----------|------|-----------|
| 核心板 BTB（CN2xx） | CN210/212/214/216/218/228/230/232/236/238/240/244/246/248/250/252/254/256/345/379/338/340/342 | GPIOH_4~8, GPIOC_7, GPIOA_0~12, GPIOAO_6/11, GPIOX_6/7/19 |
| 软排线（FPCxx） | FPC53, FPC54, FPC55, FPC56, FPC58, FPC326, FPC327, FPC328, FPC329 | GPIOA_3/4, GPIOH_4~7 |
| 板载 IC（Uxx） | U92, U84, U406, U4012, U4013 | GPIOAO_6, GPIOAO_11, GPIOX_19, GPIOX_6, GPIOX_7 |

## 待补项
- **U92 / U84 / U406 / U4012 / U4013 型号**：当前网表导出页（power 页）不含这些 IC 的组件段，需**全工程多页网表**导出后补齐型号与功能。
- **CN2xx / FPCxx 连接器型号**：同上，需全量导出。
- **GPIOA_5 等未出现引脚**：是否布线请对照完整网表确认。

> 如需补齐型号，重连 立创EDA 导出全工程网表（覆盖 A311D/BTB 页）后我再回填本表。
