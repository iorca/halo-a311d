import json
d = json.load(open('nl_parsed_full.json', encoding='utf-8'))
comps = d['comps']; nets = d['nets']

vals = {}
raw = open('nl_verify.net', 'r', encoding='utf-8', errors='replace').read()
lines = [l.rstrip('\r').rstrip() for l in raw.split('\n')]
n = len(lines); i = 0
while i < n:
    if lines[i].strip() == '[':
        i += 1; block = []
        while i < n and lines[i].strip() != '*':
            block.append(lines[i]); i += 1
        cur = {}; j = 0
        while j < len(block):
            cur[block[j].strip()] = block[j+1].strip() if j+1 < len(block) else ''
            j += 2
        des = cur.get('DESIGNATOR', '')
        if des:
            vals[des] = {'parttype': cur.get('PARTTYPE',''), 'value': cur.get('Value','')}
        i += 1
    else:
        i += 1

# RTL8211F 官方 strap:
#  pin22 PHYAD0 (PU)  pin27 PHYAD1 (PD)  pin26 PHYAD2 (PD)
#  pin24 TXDLY (PD)   pin25 RXDLY (PU)
#  pin23 PLLOFF(PD)   pin32 LED0/CFG_EXT(PD) pin33 LED1/CFG_LDO0(PU) pin34 LED2/CFG_LDO1(PD)
#  CONFIG pin: RXD3->PHYAD0, RXC->PHYAD1, RXCTL->PHYAD2, RXD2->PLLOFF,
#              RXD1->TXDLY, RXD0->RXDLY, LED0->CFG_EXT, LED1->CFG_LDO0, LED2->CFG_LDO1
# U23 引脚: .22=.22 .26=.26 .27=.27 .24=.24 .25=.25 .23=.23 .32=.32 .33=.33 .34=.34

print('=== RTL8211F strap 电平（网表实测）===')
pinmap = [
    ('PHYAD0', '22', ['R78']),   # PU
    ('PHYAD1', '27', ['R79']),   # PD
    ('PHYAD2', '26', ['R80']),   # PD
    ('TXDLY',  '24', ['R76']),   # PD -> 0 = No delay
    ('RXDLY',  '25', ['R75']),   # PU -> 1 = Add 2ns
    ('PLLOFF', '23', ['R70']),   # PD
    ('CFG_EXT','32', ['R81']),   # PD -> 0 = 用内部LDO
    ('CFG_LDO0','33', ['R84', 'R72']),  # PU
    ('CFG_LDO1','34', ['R67', 'R69']),  # PD
]
def net_of_pin(p):
    for name, m in nets.items():
        for x in m:
            if x['base'] == 'U23' and x['pin'] == p:
                return name, m
    return None, []

for cfg, pin, rs in pinmap:
    n1, m1 = net_of_pin(pin)
    # 找该引脚网络里接的电阻
    conn = []
    for x in m1:
        if x['base'] in rs:
            # 该电阻另一端接什么
            for n2, m2 in nets.items():
                for y in m2:
                    if y['base'] == x['base'] and y['pin'] == x['pin'] and n2 != n1:
                        conn.append((x['base'], n2))
    print('  ' + cfg.ljust(9) + 'pin' + pin.ljust(3) + 'net=' + str(n1).ljust(12) +
          ' strap电阻: ' + (', '.join(r + '->' + nn for r, nn in conn) if conn else '无'))

print()
print('=== 直接查每个电阻另一端接电源还是地 ===')
for r in ['R78', 'R79', 'R80', 'R76', 'R75', 'R74', 'R77', 'R70', 'R71', 'R81', 'R84', 'R72', 'R67', 'R69']:
    for name, m in nets.items():
        if name in ('GND', 'A_3V3', 'VCC5V', 'VDDIO_AO18', 'VDDCPU_B_EN', 'VCC1.8V', 'A_1V8'):
            for x in m:
                if x['base'] == r:
                    print('  ' + r.ljust(5) + '[' + str(vals.get(r, {}).get('value')) + '] -> ' + name)