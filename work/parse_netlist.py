import json, re, sys

def parse_netlist(path):
    raw = open(path, encoding='utf-8').read()
    toks = [l.strip() for l in raw.split('\n') if l.strip() != '']
    components = {}
    nets = {}
    i = 0
    n = len(toks)
    cur = None
    mode = None
    net_name = None
    while i < n:
        s = toks[i]
        if s == ',[,' or s == ',[=' or s == '[':
            i += 1; continue
        if s == ',[':
            mode = 'comp'; cur = {}; i += 1; continue
        if s in (',*', ', *', '*,', ',]', ', ]') or s.startswith(',]'):
            if mode == 'comp' and cur.get('designator'):
                components[cur['designator']] = cur
            mode = None; cur = None; i += 1; continue
        if s == ',(':
            mode = 'net'; net_name = None; i += 1; continue
        if s == ',)':
            mode = None; net_name = None; i += 1; continue
        if mode == 'comp':
            if s.startswith(',') and i + 1 < n:
                key = s[1:].strip()
                # value may be on following token(s); take next token (skip if it's a key-like comma line? no)
                val = toks[i+1]
                cur[key.lower()] = val.lstrip(',').strip()
                i += 2
                continue
            i += 1; continue
        if mode == 'net':
            if net_name is None:
                net_name = s.lstrip(',').strip()
                nets.setdefault(net_name, [])
                i += 1; continue
            body = s.lstrip(',')
            m = re.match(r'^([A-Za-z0-9_]+)-([A-Za-z0-9]+)\b', body)
            if m:
                nets[net_name].append((m.group(1), m.group(2)))
            i += 1; continue
        i += 1
    return components, nets

if __name__ == '__main__':
    comps, nets = parse_netlist('nl.net')
    print("components:", len(comps), "nets:", len(nets))
    out = {'components': comps, 'nets': nets}
    json.dump(out, open('netlist_parsed.json', 'w'), ensure_ascii=False)
    print("wrote netlist_parsed.json")
