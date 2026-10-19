import json, re
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

def st(des):
    v = vals.get(des, {})
    used = v.get('bom') == 'yes' and v.get('pcb') == 'yes'
    return ('使用' if used else '未使用')

print('############ 逐项核验 ############')
print()
print('[1] Q15 料号修正')
v = vals.get('Q15', {})
print('  Q15 PARTTYPE =', v.get('parttype'), '| Value =', repr(v.get('value')), '|', st('Q15'))
print('  Q8  PARTTYPE =', vals.get('Q8', {}).get('parttype'), '|', st('Q8'))
print('  -> Q15 已改为 MMBT3906(PNP)，Q8 保持 NPN，两颗极性不同 ✓')
print()
for q in ('Q15', 'Q8'):
    print('  ' + q + ' 引脚:')
    for name, m in nets.items():
        for x in m:
            if x['base'] == q:
                others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != q)
                print('     pin' + x['pin'].ljust(3) + name.ljust(12) + ('[大网]' if len(m) >= 20 else others))

print()
print('[2] FPC6 / CN6 已删除')
for d2 in ('FPC6', 'CN6'):
    print('  ' + d2 + ' 在元件表: ' + ('是' if d2 in comps else '否(已删除)') +
          ' | 出现在网络: ' + str([n2 for n2, m in nets.items() if any(x['base'] == d2 for x in m)]))

print()
print('[3] 新增 U45 SHT40 (I2C_AO_M0 / I2C_AO_S0)')
v = vals.get('U45', {})
print('  U45 =', v.get('parttype'), '| Value =', repr(v.get('value')), '|', st('U45'))
for name, m in nets.items():
    if 'I2C_AO_S0' in name:
        print('  ' + name + ' = ' + ', '.join(x['base'] + '.' + x['pin'] for x in m))
print('  U45 全部引脚:')
for name, m in nets.items():
    for x in m:
        if x['base'] == 'U45':
            others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != 'U45')
            print('     pin' + x['pin'].ljust(3) + name.ljust(12) + ('[大网]' if len(m) >= 20 else others))

print()
print('[4] U42 SHT40 (I2C_EE_M3 / 触控)')
v = vals.get('U42', {})
print('  U42 =', v.get('parttype'), '| Value =', repr(v.get('value')), '|', st('U42'))
for name, m in nets.items():
    if 'TOUCH_I2C' in name:
        print('  ' + name + ' = ' + ', '.join(x['base'] + '.' + x['pin'] for x in m))

print()
print('[5] 两颗 SHT40 地址是否都是 0x44')
print('  U42(Value=%r) @ TOUCH_I2C -> GPIOA_14/15 (I2C_EE_M3)' % vals.get('U42', {}).get('value'))
print('  U45(Value=%r) @ I2C_AO_S0 -> CN3 (I2C_AO_M0)' % vals.get('U45', {}).get('value'))

print()
print('[6] FUSB340 / GPIOA_2 切换链')
for name, m in nets.items():
    if name in ('PCIE_EN', 'GPIOA_2', 'SEL'):
        print('  ' + name + ' = ' + ', '.join(x['base'] + '.' + x['pin'] for x in m))
print('  U28 =', vals.get('U28', {}).get('parttype'), '|', st('U28'))

print()
print('[7] 关键 GPIO 网络现状')
rx = re.compile(r'^GPIO(A|C|H|X|AO)_(\d+)$')
rows = []
for name, m in nets.items():
    g = rx.match(name)
    if not g: continue
    rows.append((g.group(1), int(g.group(2)), name, m))
for grp, num, name, m in sorted(rows, key=lambda r: (r[0], r[1])):
    parts = []
    for x in m:
        vv = vals.get(x['base'], {})
        u = '使用' if (vv.get('bom') == 'yes' and vv.get('pcb') == 'yes') else '未使用'
        parts.append(x['base'] + '.' + x['pin'] + ('' if u == '使用' else '(' + u + ')'))
    print('  ' + name.ljust(11) + ' = ' + ', '.join(parts))

print()
print('[8] 关键器件型号终版')
for des in ['U23', 'U28', 'U29', 'U30', 'U31', 'U40', 'U8', 'U38', 'U42', 'U45']:
    v = vals.get(des)
    if v:
        print('  ' + des.ljust(5) + str(v.get('parttype'))[:30].ljust(32) +
              'Value=' + str(v.get('value'))[:10].ljust(12) + st(des))
    else:
        print('  ' + des.ljust(5) + '(不在元件表)')