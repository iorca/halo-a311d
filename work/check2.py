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

def st(d_):
    v = vals.get(d_, {})
    return '使用' if (v.get('bom') == 'yes' and v.get('pcb') == 'yes') else '未使用'

print('[A] GPIOAO_10 / SYS_LED 完整链（运行灯逻辑）')
for name, m in sorted(nets.items()):
    if name in ('SYS_LED', '$5N599', '$5N603', '$5N602'):
        print('  ' + name + ':')
        for x in m:
            print('     ' + x['base'] + '.' + x['pin'] + '[' +
                  str(vals.get(x['base'], {}).get('parttype')) + '] Value=' +
                  str(vals.get(x['base'], {}).get('value')) + ' ' + st(x['base']))
print('  Q8 料号 =', vals.get('Q8', {}).get('parttype'), '|', st('Q8'))

print()
print('[B] GPIOAO_11 网络 + U8(MT9700) 引脚')
for name, m in sorted(nets.items()):
    if name == 'GPIOAO_11':
        print('  ' + name + ':')
        for x in m:
            print('     ' + x['base'] + '.' + x['pin'] + '[' +
                  str(vals.get(x['base'], {}).get('parttype')) + ']' + st(x['base']))
print('  U8 = MT9700 小信号引脚:')
for name, m in sorted(nets.items()):
    for x in m:
        if x['base'] == 'U8' and len(m) <= 6:
            others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != 'U8')
            print('     pin' + x['pin'].ljust(4) + name.ljust(16) + others)

print()
print('[C] GPIOA_7 现状')
for name, m in sorted(nets.items()):
    if name == 'GPIOA_7':
        print('  GPIOA_7:')
        for x in m:
            print('     ' + x['base'] + '.' + x['pin'] + '[' +
                  str(vals.get(x['base'], {}).get('parttype')) + ']' + st(x['base']))

print()
print('[D] U31 SL6341D 全部引脚')
for name, m in nets.items():
    for x in m:
        if x['base'] == 'U31':
            others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != 'U31' and len(m) < 25)
            print('  U31 pin' + x['pin'].ljust(4) + name.ljust(18) + ('[大网]' if len(m) >= 25 else others))
print('  U31 =', vals.get('U31', {}).get('parttype'), '| fp =', vals.get('U31', {}).get('fp'), '|', st('U31'))

print()
print('[E] 板上其它复位/使能类信号')
for name, m in sorted(nets.items()):
    if re.search(r'RST|RESET|RSTN|_EN$|_EN_', name) and len(m) <= 6:
        parts = []
        for x in m:
            parts.append(x['base'] + '.' + x['pin'] + '[' + str(vals.get(x['base'], {}).get('parttype')) + ']' + ('' if st(x['base']) == '使用' else '(未使用)'))
        print('  ' + name.ljust(20) + ' = ' + ', '.join(parts))