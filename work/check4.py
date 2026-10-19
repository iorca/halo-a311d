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
            vals[des] = {'parttype': cur.get('PARTTYPE',''), 'value': cur.get('Value',''),
                         'fp': cur.get('FOOTPRINT',''),
                         'bom': cur.get('Add into BOM',''), 'pcb': cur.get('Convert to PCB','')}
        i += 1
    else:
        i += 1

def other_end(r):
    """返回电阻另一端接的电源网名"""
    for name, m in nets.items():
        for x in m:
            if x['base'] == r and len(m) <= 3:
                for y in m:
                    if y['base'] != r and y['base'] != 'U23':
                        return name
    return '?'

def pop(r):
    v = vals.get(r, {})
    return (v.get('bom') == 'yes' and v.get('pcb') == 'yes')

print('=== RTL8211F strap 电阻：贴装状态 + 接向 ===')
rows = [
    ('TXDLY  (pin24/RXD1)', ['R76', 'R77']),
    ('RXDLY  (pin25/RXD0)', ['R74', 'R75']),
    ('PHYAD0 (pin22/RXD3)', ['R78']),
    ('PHYAD1 (pin27/RXC)',  ['R79']),
    ('PHYAD2 (pin26/RXCTL)',['R80']),
    ('PLLOFF (pin23/RXD2)', ['R70', 'R71']),
    ('CFG_EXT(pin32/LED0)', ['R81']),
    ('CFG_LDO0(pin33/LED1)',['R84', 'R72']),
    ('CFG_LDO1(pin34/LED2)',['R67', 'R69']),
]
for cfg, rs in rows:
    print('  ' + cfg)
    for r in rs:
        v = vals.get(r, {})
        mark = '贴' if pop(r) else '★不贴'
        print('     ' + r.ljust(5) + mark.ljust(8) + 'Value=' + str(v.get('value')).ljust(9) +
              ' 接: ' + other_end(r))

print()
print('=== ETH_VDDIO 实际供电来源 ===')
for name, m in nets.items():
    if name == 'ETH_VDDIO':
        for x in m:
            print('   ' + x['base'] + '.' + x['pin'] + '[' + str(vals.get(x['base'], {}).get('parttype')) + ']')
print('  R26/R27 另一端:')
for r in ['R26', 'R27']:
    print('     ' + r + ' -> ' + str(other_end(r)))

print()
print('=== U22 (LMD4030) 是什么 ===')
v = vals.get('U22', {})
print('  U22 =', v.get('parttype'), '| Value=', v.get('value'), '| fp=', str(v.get('fp'))[:30])
for name, m in nets.items():
    for x in m:
        if x['base'] == 'U22' and len(m) <= 6:
            others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != 'U22')
            print('     pin' + x['pin'].ljust(3) + name.ljust(14) + others)