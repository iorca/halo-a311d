import io, re

src = io.open('meson-althaea-a311d.dts', encoding='utf-8').read()

# 1. 改 model / compatible
s = src.replace(
    'model = "Althea A311D (MAIN_V0.3)";',
    'model = "Althea A311D (MAIN_V0.3) PCIe";')

# 2. 文件头加变体说明
hdr_old = ' * MAIN_V0.3 — Althea A311D board\n'
hdr_new = (' * MAIN_V0.3 — Althea A311D board 【PCIe 模式变体】\n'
           ' *\n'
           ' * 本文件是 meson-althaea-a311d.dts 的 PCIe 变体，差异：\n'
           ' *   &pcie status="okay" + reset-gpios(GPIOA_0 PERST#)\n'
           ' *   &usb  status="disabled"\n'
           ' *   FUSB340 SEL 需为 HIGH（见本文件末尾 PCIe 说明段）\n'
           ' *\n'
           ' * 用法：/boot/extlinux/extlinux.conf 里改 fdt 行冷切换\n'
           ' *     LABEL Althea-USB3 : FDT /boot/meson-althaea-usb3.dtb\n'
           ' *     LABEL Althea-PCIe : FDT /boot/meson-althaea-pcie.dtb\n')
s = s.replace(hdr_old, hdr_new, 1)

# 3. pcie 段：disabled -> okay + reset-gpios
old_pcie = '''&pcie {
\tstatus = "disabled";       /* 切 PCIe 时改为 "okay" 并在对应 DTB 中启用 usb */
\t/* 切 PCIe 时需一并启用：
\treset-gpios = <&gpio GPIOA_0 GPIO_ACTIVE_LOW>;   /* M.2 PERST#，4.7k上拉，低有效 */
\t */
\t/* 参考(VIM3 用 GPIOA_8，本板改用 GPIOA_0) */

\t/* PCI 侧唤醒（内核支持时启用）：
\twakeup-gpios = <&gpio GPIOA_1 GPIO_ACTIVE_HIGH>;   /* PEWAKE */
\twakeup-source;                                     /* CLKREQ# (GPIOC_7, 4.7k下拉) */
\t */
};'''
new_pcie = '''/* PCIe 模式启用（本变体）
 * reset: M.2 PERST# = GPIOA_0，4.7k 上拉 A_3V3，低有效
 *        参考 VIM3 用 GPIOA_8，本板实测为 GPIOA_0
 */
&pcie {
\tstatus = "okay";
\treset-gpios = <&gpio GPIOA_0 GPIO_ACTIVE_LOW>;

\t/* 若内核/设备支持从 PCIe 唤醒，再启用以下两项：
\twakeup-gpios = <&gpio GPIOA_1 GPIO_ACTIVE_HIGH>;  * PEWAKE (4.7k上拉)
\twakeup-source;                                     * CLKREQ# (GPIOC_7, 4.7k下拉)
\t */
};'''
assert old_pcie in s, 'pcie 段未匹配'
s = s.replace(old_pcie, new_pcie, 1)

# 4. usb 段：okay -> disabled
old_usb = '''&usb {
\tstatus = "okay";
\tdr_mode = "peripheral";
};'''
new_usb = '''/* PCIe 模式下USB3.0 关闭（PHY 已归 pcie，见 usb3_pcie_phy 说明） */
&usb {
\tstatus = "disabled";
\tdr_mode = "peripheral";
};'''
assert old_usb in s, 'usb 段未匹配'
s = s.replace(old_usb, new_usb, 1)

# 5. pcie 说明段的"当前配置"改成 PCIe 模式提示
s = s.replace(
    ' * 【当前配置】默认只开 USB3.0\n',
    ' * 【当前配置】本文件为 PCIe 模式：&pcie okay / &usb disabled\n'
    ' *   USB3.0 变体见meson-althaea-a311d.dts（&usb okay / &pcie disabled）\n')

# 6. FUSB340 hog 默认电平提示（本变体需HIGH，但硬件下拉，需 bootloader 或改硬件）
s = s.replace(
    '\t\toutput-low;\n\t\tline-name = "FUSB340_SEL";',
    '\t\toutput-low;      /* ⚠ 本变体为 PCIe 模式，SEL 需 HIGH！\n'
    '\t\t                 *   硬件 R85/R87 4.7k 下拉 → 实际仍为 LOW。\n'
    '\t\t                 *   必须由 U-Boot 在 boot 前拉高 GPIOA_2，或改硬件为上拉。\n'
    '\t\t                 */\n'
    '\t\tline-name = "FUSB340_SEL";')

io.open('meson-althaea-pcie.dts', 'w', encoding='utf-8').write(s)

# 校验
s2 = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
s2 = re.sub(r'//[^\n]*', '', s2)
d = 0; bad = None; line = 1
for ch in s2:
    if ch == '\n': line += 1
    elif ch == '{': d += 1
    elif ch == '}':
        d -= 1
        if d < 0 and bad is None: bad = line
print('生成 meson-althaea-pcie.dts')
print('{ =', s2.count('{'), '} =', s2.count('}'), '注释', s.count('/*'), s.count('*/'))
print('平衡:', 'YES' if d == 0 and bad is None and s.count('/*') == s.count('*/') else 'NO bad@%s' % bad)
print('行数:', len(s.split('\n')))