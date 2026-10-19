import io

NEW = '''/* ==================================================================
 * SPI 屏（FPC5）—— 硬件 SPI1（GPIOH_4~7）
 * ==================================================================
 * 规格书 A311D Table 3-26 (GPIO_x Multi-Function Pin) 与
 * mainline drivers/pinctrl/meson/pinctrl-meson-g12a.c 双向确认：
 *
 *   规格书 bit 字段         GPIO      驱动 group    pinctrl function
 *   ----------------------  --------  ------------  ---------------
 *   bit31-24  SPI_B_MOSI    GPIOH_4   spi1_mosi     "spi1"
 *   bit23-16  SPI_B_SCLK    GPIOH_7   spi1_clk      "spi1"
 *   bit15-8   SPI_B_SS0     GPIOH_6   spi1_ss0      "spi1"
 *   bit7-0    SPI_B_MISO    GPIOH_5   spi1_miso     "spi1"
 *
 *   驱动原文 (pinctrl-meson-g12a.c):
 *     186: spi1_mosi_pins[] = { GPIOH_4 };
 *     187: spi1_miso_pins[] = { GPIOH_5 };
 *     188: spi1_ss0_pins[]  = { GPIOH_6 };
 *     189: spi1_clk_pins[]  = { GPIOH_7 };
 *
 *   注意命名差异：规格书称 SPI_B（SoC 第 2 个 SPI），
 *   mainline pinctrl 驱动称 spi1_*，SoC 节点名为 spi1。
 *
 *   CS = SPI_B_SS0 = GPIOH_6（不是 GPIOH_7）；SCLK = GPIOH_7。
 *
 * 屏控制 GPIO（与 SPI 控制器无关）：
 *   GPIOA_3 = SPI_RST(屏复位)   GPIOA_4 = SPI_RS(寄存器选择)
 *   GPIOH_8 = 背光 EN -> Q15(MMBT3906 PNP 高边) -> ACTIVE_LOW
 */

/* SPI_B 控制器 = SPI1，GPIOH_4~7 */
&spi1 {
\tstatus = "okay";

\tpinctrl-0 = <&spi1_mosi>, <&spi1_miso>, <&spi1_clk>;
\tpinctrl-names = "default";

\tnum-cs = <1>;
\tcs-gpios = <&gpio GPIOH_6 GPIO_ACTIVE_LOW>;\t/* SPI_B_SS0 */

\tmax-frequency = <24000000>;\t/* 小屏 24MHz 足够，保守取值 */

\t/* 屏初始化序列通常在屏驱动中，不在 DTS */
};

/* 屏控制 GPIO */
&gpio_ctrl {
\t/* 屏复位：极性按屏模组手册 */
\tlcd-rst-gpios = <&gpio GPIOA_3 GPIO_ACTIVE_HIGH>;
\t/* 屏寄存器选择 (Register Select) */
\tlcd-rs-gpios  = <&gpio GPIOA_4 GPIO_ACTIVE_HIGH>;
\t/* 背光：GPIOH_8 -> Q15(MMBT3906 PNP 高边) -> 拉低导通 -> 点亮 */
\tbacklight-gpios = <&gpio GPIOH_8 GPIO_ACTIVE_LOW>;
};
'''

src = io.open('meson-althaea-a311d.dts', encoding='utf-8').read()
lines = src.split('\n')

# 定位替换区间：从 SPI 屏注释块起点，到 &gpio_ctrl{...}; 结束
start = None
for i, l in enumerate(lines):
    if 'SPI 屏（FPC5）' in l:
        start = i - 1   # 指向上面的 /* ==== 开行
        break
assert start is not None, 'start not found'

# 从 start 往后找第一个以 "};" 结尾的行（&gpio_ctrl 块的结束）
end = None
for j in range(start, len(lines)):
    if lines[j].rstrip() == '};':
        end = j
        break
assert end is not None, 'end not found'

out = lines[:start] + NEW.split('\n') + lines[end + 1:]
io.open('meson-althaea-a311d.dts', 'w', encoding='utf-8').write('\n'.join(out))
print('replaced lines %d..%d' % (start + 1, end + 1))
print('--- new SPI section ---')
print('\n'.join(NEW.split('\n')[:8]))