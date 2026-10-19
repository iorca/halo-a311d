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

print('=== R85 / R87 / R86 / R123 每一脚所在网络 ===')
for r in ['R85', 'R86', 'R87', 'R123']:
    for name, m in nets.items():
        for x in m:
            if x['base'] == r:
                others = ', '.join(y['base'] + '.' + y['pin'] for y in m if y['base'] != r)
                big = '[电源/地大网]' if len(m) >= 20 else others
                print('  ' + r + '.' + x['pin'] + ' -> ' + name.ljust(14) +
                      '[' + str(vals.get(r, {}).get('value')) + '] ' + big)

print()
print('=== GPIOA_2 完整网络 ===')
for name, m in nets.items():
    if name == 'GPIOA_2':
        print(' 成员: ' + ', '.join(x['base'] + '.' + x['pin'] for x in m))

print()
print('=== 对照：PCIe 三脚的偏置（已验证）===')
for r in ['R88', 'R89', 'R90', 'R91', 'R92', 'R93']:
    for name, m in nets.items():
        if name in ('GND', 'A_3V3'):
            for x in m:
                if x['base'] == r:
                    print('  ' + r + '[' + str(vals.get(r, {}).get('value')) + '] -> ' + name)