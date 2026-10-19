#!/usr/bin/env python3
"""解析 Protel2 网表。元件段内部空行=空值，必须保留，不能过滤。"""
import json, sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "nl_full_project.net"
raw = open(PATH, "r", encoding="utf-8", errors="replace").read()
# 保留所有行，仅去掉 \r 和行尾空白；空行是"空值"，不可删
lines = [l.rstrip("\r").rstrip() for l in raw.split("\n")]

n = len(lines)

comps = {}
i = 0
while i < n:
    if lines[i].strip() == "[":
        i += 1
        block = []
        while i < n and lines[i].strip() != "*":
            block.append(lines[i])
            i += 1
        cur = {}
        j = 0
        while j < len(block):
            key = block[j].strip()
            val = block[j + 1].strip() if j + 1 < len(block) else ""
            cur[key] = val
            j += 2
        d = cur.get("DESIGNATOR", "")
        if d:
            comps[d] = {
                "footprint": cur.get("FOOTPRINT", ""),
                "parttype": cur.get("PARTTYPE", ""),
                "mp": cur.get("Manufacturer Part", cur.get("PARTTYPE", "")),
                "lcsc": cur.get("LCSC Part Name", ""),
                "add_bom": cur.get("Add into BOM", ""),
                "to_pcb": cur.get("Convert to PCB", ""),
            }
        i += 1
    else:
        i += 1

nets = {}
i = 0
while i < n:
    if lines[i].strip() == "(":
        i += 1
        name = lines[i].strip().split(" ")[0] if i < n else ""
        i += 1
        members = []
        while i < n and lines[i].strip() != ")":
            toks = lines[i].strip().split()
            if toks:
                desig = toks[0]
                base, pin = desig.rsplit("-", 1) if "-" in desig else (desig, "?")
                members.append({"base": base, "pin": pin, "value": " ".join(toks[1:])})
            i += 1
        if name:
            nets[name] = members
        i += 1
    else:
        i += 1

import collections
cb = collections.Counter(c["add_bom"] for c in comps.values())
cp = collections.Counter(c["to_pcb"] for c in comps.values())
used = [d for d, c in comps.items() if c["add_bom"].lower() == "yes" or c["to_pcb"].lower() == "yes"]
print(f"元件总数: {len(comps)}  网络: {len(nets)}")
print("Add into BOM 分布:", dict(cb))
print("Convert to PCB 分布:", dict(cp))
for k in ["U6", "CN2", "U40", "R13", "C1"]:
    if k in comps:
        print(k, {kk: vv for kk, vv in comps[k].items() if kk in ("parttype", "add_bom", "to_pcb")})
json.dump({"comps": comps, "nets": nets}, open("nl_parsed_full.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written nl_parsed_full.json  used(any yes)=", len(used))