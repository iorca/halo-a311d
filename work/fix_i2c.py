import io, re

NEW = '''/* ==================================================================
 * I2C —— 两颗 SHT40
 * ==================================================================
 * U42 @ I2C3 (GPIOA_14=SDA / GPIOA_15=SCL, EE 域, A_3V3 供电)
 *      规格书复用名 I2C_EE_M3_SDA / I2C_EE_M3_SCL
 *      驱动确认 (drivers/pinctrl/meson/pinctrl-meson-g12a.c):
 *        216: i2c3_sda_a_pins[] = { GPIOA_14 };
 *        217: i2c3_sck_a_pins[] = { GPIOA_15 };
 *      i2c3 节点: meson-g12-common.dtsi:2373  (i2c@1c000)
 *      参照: VIM3 亦用此组 (meson-khadas-vim3.dtsi:339)
 *
 * U45 @ I2C_AO (AO 域, VDDIO_AO18 1.8V 供电)
 *
 * 注意：两颗同地址 0x44 但在**两个独立 I2C 控制器**上，合法共存。
 *       切勿挂到同一 &i2c 下（地址冲突 -> 总线锁死）。
 */

/* U42 SHT40 —— I2C3 @ GPIOA_14(SDA)/GPIOA_15(SCL) */
&i2c3 {
\tstatus = "okay";
\tpinctrl-0 = <&i2c3_sda_a_pins>, <&i2c3_sck_a_pins>;
\tpinctrl-names = "default";
\tclock-frequency = <100000>;

\tsht40_ee: sht40@44 {
\t\tcompatible = "sensirion,sht4x";
\t\treg = <0x44>;
\t};
};

/* U45 SHT40 —— I2C_AO (AO 域) */
&i2c_AO {
\tstatus = "okay";
\tpinctrl-0 = <&i2c_ao_sck_pins>, <&i2c_ao_sda_pins>;
\tpinctrl-names = "default";

\trtc: rtc@51 {
\t\tcompatible = "haoyu,hym8563";
\t\treg = <0x51>;
\t\t#clock-cells = <0>;
\t};

\tsht40_ao: sht40@44 {
\t\tcompatible = "sensirion,sht4x";
\t\treg = <0x44>;
\t};
};
'''

src = io.open('meson-althaea-a311d.dts', encoding='utf-8').read()
lines = src.split('\n')

# 定位：找 "I2C —— 两颗 SHT40" 注释块起点，回退到 /* ==== 行
start = None
for i, l in enumerate(lines):
    if 'I2C —— 两颗 SHT40' in l:
        start = i - 1
        break
assert start is not None

# 往后找本段结束：连续遇到两个空行+下一段注释，或找到 'I2C_AO {' 块的结束
end = None
for j in range(start, len(lines)):
    if lines[j].rstrip() == '};' and'i2c_AO' in'\n'.join(lines[max(start,j-30):j]):
        end = j
        break
assert end is not None, 'end not found'

# 再往后确认没有残留的旧注释块（找到下一个 "/* ====" 段起点）
tail = None
for j in range(end + 1, len(lines)):
    s = lines[j].strip()
    if s.startswith('/* ====='):
        tail = j
        break

out = lines[:start] + NEW.split('\n') + lines[tail:]
io.open('meson-althaea-a311d.dts', 'w', encoding='utf-8').write('\n'.join(out))
print('replaced lines %d..%d' % (start + 1, end + 1))
print('next section at line', tail + 1)