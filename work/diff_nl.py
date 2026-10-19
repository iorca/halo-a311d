import json
old = json.load(open('nl_parsed_old.json', encoding='utf-8'))
new = json.load(open('nl_parsed_full.json', encoding='utf-8'))

oc, nc = old['comps'], new['comps']
on, nn = old['nets'], new['nets']

print('=== 新增网络 ===')
for k in sorted(set(nn) - set(on)):
    print('  + ' + k + ' = ' + ', '.join(x['base'] + '.' + x['pin'] for x in nn[k]))
print()
print('=== 删除网络 ===')
for k in sorted(set(on) - set(nn)):
    print('  - ' + k + ' = ' + ', '.join(x['base'] + '.' + x['pin'] for x in on[k]))
print()
print('=== 成员变化的网络 ===')
cnt = 0
for k in sorted(set(on) & set(nn)):
    a = sorted(x['base'] + '.' + x['pin'] for x in on[k])
    b = sorted(x['base'] + '.' + x['pin'] for x in nn[k])
    if a != b:
        cnt += 1
        add = set(b) - set(a); rem = set(a) - set(b)
        print('  ~ ' + k)
        if add: print('      + ' + ', '.join(sorted(add)))
        if rem: print('      - ' + ', '.join(sorted(rem)))
print('  变化网络数:', cnt)
print()
print('=== 元件属性变化 ===')
for k in sorted(set(oc) & set(nc)):
    if oc[k] != nc[k]:
        for f in ('parttype', 'add_bom', 'to_pcb'):
            if oc[k].get(f) != nc[k].get(f):
                print('  ' + k + '  ' + f + ': ' + str(oc[k].get(f)) + ' -> ' + str(nc[k].get(f)))
print()
print('=== 新增/删除元件 ===')
for k in sorted(set(nc) - set(oc)):
    print('  + ' + k + '  ' + str(nc[k].get('parttype')) + '  bom=' + str(nc[k].get('add_bom')))
for k in sorted(set(oc) - set(nc)):
    print('  - ' + k + '  ' + str(oc[k].get('parttype')) + '  bom=' + str(oc[k].get('add_bom')))