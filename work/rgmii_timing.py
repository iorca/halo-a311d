# RGMII 时序分析 —— 基于 PCB 等长网络组实测长度
# 数据来源：立创EDA 网络组面板截图（GMAC0_TX / PHY0_RX 两组）
#
# 关键换算：FR4 走线约 0.15 ns/inch ≈ 0.00015 ns/mil
#        RGMII 规范要求 clock 与 data 之间偏移 2.0 ns
#        → 2ns 若靠 PCB 走线实现，需约 13000 mil (13 inch) ！
#        → 所以业界一律用 PHY 内部延迟线或 MAC 寄存器，不用 PCB 补偿

NS_PER_MIL = 0.00015# ns/mil

tx = {
    'GMAC0_TXCLK': 485.1,
    'GMAC0_TXD3':  484.2,
    'GMAC0_TXEN':  483.5,
    'GMAC0_TXD0':  481.9,
    'GMAC0_TXD1':  480.2,
    'GMAC0_TXD2':  478.6,
}
rx = {
    'PHY0_RXCLK/PHYAD1': 755.9,
    'PHY0_RXD1/TXDLY':   755.9,
    'PHY0_RXD3/PHYAD0':  755.9,
    'PHY0_RXDV/PHYAD2':  755.9,
    'PHY0_RXD0/RXDLY':   751.8,
    'PHY0_RXD2/PLLOFF':  748.6,
}

def analyze(name, g):
    vals = list(g.values())
    mx, mn = max(vals), min(vals)
    spread = mx - mn
    clk_key = [k for k in g if 'CLK' in k][0]
    clk = g[clk_key]
    data = [v for k, v in g.items() if 'CLK' not in k]
    dmax, dmin = max(data), min(data)
    # clock 相对 data 的偏移
    clk_minus_longest_data = clk - dmax
    clk_minus_shortest_data = clk - dmin
    print('=' * 62)
    print('【' + name + '】共 ' + str(len(g)) + ' 根')
    for k, v in sorted(g.items(), key=lambda x: -x[1]):
        print('    ' + k.ljust(20) + str(v).rjust(7) + ' mil')
    print('  --')
    print('  组内长度散布     : ' + str(round(spread, 1)) + ' mil  = ' +
          format(spread * NS_PER_MIL * 1000, '.3f') + ' ps')
    print('  时钟(' + clk_key[:12] + ') : ' + str(clk) + ' mil')
    print('  数据线范围       : ' + str(dmin) + ' ~ ' + str(dmax) + ' mil')
    print('  clock - 最长data : ' + str(round(clk_minus_longest_data, 1)) + ' mil  = ' +
          format(clk_minus_longest_data * NS_PER_MIL * 1000, '.3f') + ' ps')
    print('  clock - 最短data : ' + str(round(clk_minus_shortest_data, 1)) + ' mil  = ' +
          format(clk_minus_shortest_data * NS_PER_MIL * 1000, '.3f') + ' ps')
    print('  RGMII 需求偏移   : 2000 ps  (2.0 ns)')
    ratio = abs(clk_minus_longest_data) * NS_PER_MIL * 1000 / 2000.0 * 100
    print('  → PCB 提供的偏移占比: ' + format(ratio, '.4') + ' %  (远不够)')
    print()

analyze('TX 方向 (MAC -> PHY)', tx)
analyze('RX 方向 (PHY -> MAC)', rx)

print('=' * 62)
print('结论：')
print('  1. 两组均为"等长设计"(组内散布 <8 mil ≈ 1 ps)，非"故意时钟偏移"')
print('  2. TXC 虽为组内最长，但仅比最长数据线长 0.9 mil ≈ 0.14 ps')
print('  3. PCB 提供的 clock-data 偏移 ≈ 0.14 ps  <<  需求 2000 ps')
print('  4. → RGMII 的 2ns 延时 **完全依赖 PHY 内部延迟线或 MAC 寄存器**')
print('  5. → 必须用 phy-mode 让驱动显式使能 PHY 的 TX+RX 延迟')
print('     即 phy-mode = "rgmii-id"（驱动软件写 PHY 寄存器强制双向 2ns）')
print()
print('另：2ns 靠 PCB 走线需 ~13000 mil，与实际组内 ~500-750 mil 相差一个数量级，')
print('    也印证业界从不用 PCB 补偿 RGMII 延时。')