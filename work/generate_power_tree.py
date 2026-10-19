#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate MAIN_V0.3 power tree SVG from verified netlist topology."""
import json

# ---- node registry: id -> (cx, cy, title, sub, fill) ----
W, H = 150, 46
NODES = {
    # INPUT level
    "dc_in":  (200, 130, "DC_IN", "筒形插座 CN12/14/16/18/110/112 + U21功放", "#e67e22"),
    "dc_inb": (620, 130, "DC_INB", "USB-C VBUS USB1 B9/A9/B4/A4", "#e67e22"),
    "oring":  (410, 130, "Q35-Q39 + D21", "理想二极管 OR-ing", "#d35400"),
    "ch224k": (985, 130, "CH224K (U6)", "PD 协商芯片 CC1/CC2/D+/D-", "#16a085"),
    # MERGE
    "vin":    (410, 235, "DC_IN (合并)", "NB680GD VIN (U1/U2 pin1)", "#34495e"),
    # PMIC
    "u1":     (250, 345, "U1 NB680GD", "3.3V PMIC", "#2980b9"),
    "u2":     (570, 345, "U2 NB680GD", "5V PMIC", "#2980b9"),
    # RAILS
    "a33":    (120, 475, "A_3V3", "主 3.3V (U1 buck)", "#27ae60"),
    "ldo33":  (300, 475, "LDO_3V3", "U1 内部 LDO", "#27ae60"),
    "nbv3":   (450, 475, "NB_V3", "U1 3.3V", "#27ae60"),
    "vcc5":   (640, 475, "VCC5V", "主 5V (U2 buck)", "#c0392b"),
    "nbv5":   (820, 475, "NB_V5", "U2 5V", "#c0392b"),
    # SECONDARY converters
    "u7":     (120, 615, "U7 SY8088", "3.3V buck (并联 U1)", "#8e44ad"),
    "u3":     (300, 615, "U3 RT9013", "1.8V LDO", "#8e44ad"),
    "u4":     (450, 615, "U4 RT9013", "1.8V LDO", "#8e44ad"),
    "u8":     (640, 615, "U8 MT9700", "负载开关", "#8e44ad"),
    "u32":    (820, 615, "U32 MT9700", "负载开关", "#8e44ad"),
    "u33":    (980, 615, "U33 MT9700", "负载开关", "#8e44ad"),
    # OUTPUTS / LOADS
    "loads33":(120, 765, "A_3V3 负载", "SoC / Q11-Q18 等", "#95a5a6"),
    "ao18":   (300, 765, "VDDIO_AO18", "SoC AO 域", "#95a5a6"),
    "v18":    (450, 765, "VCC1.8V", "1.8V 负载", "#95a5a6"),
    "usb4":   (640, 765, "5V_OTG", "→ USB4", "#95a5a6"),
    "usb2":   (820, 765, "VBUS_1", "→ USB2", "#95a5a6"),
    "usb3":   (980, 765, "VBUS_2", "→ USB3", "#95a5a6"),
}

# edges: (src, tgt, style, label, src_anchor, tgt_anchor)
# style: 'solid' (confirmed) | 'dash' (to verify)
EDGES = [
    ("dc_in",  "oring",  "solid", "", "right", "left"),
    ("dc_inb", "oring",  "solid", "", "left",  "right"),
    ("oring",  "vin",    "solid", "", "bottom","top"),
    ("ch224k", "oring",  "dash",  "控制栅极", "left", "right"),
    ("vin",    "u1",     "solid", "", "bottom","top"),
    ("vin",    "u2",     "solid", "", "bottom","top"),
    ("u1",     "a33",    "solid", "", "bottom","top"),
    ("u1",     "ldo33",  "solid", "", "bottom","top"),
    ("u1",     "nbv3",   "solid", "", "bottom","top"),
    ("u2",     "vcc5",   "solid", "", "bottom","top"),
    ("u2",     "nbv5",   "solid", "", "bottom","top"),
    ("a33",    "loads33","solid", "", "bottom","top"),
    ("vcc5",   "u7",     "dash",  "VIN 待确认", "bottom","top"),
    ("u7",     "a33",    "solid", "并联 buck", "top", "bottom"),
    ("a33",    "u3",     "solid", "", "bottom","top"),
    ("u3",     "ao18",   "solid", "", "bottom","top"),
    ("a33",    "u4",     "solid", "", "bottom","top"),
    ("u4",     "v18",    "solid", "", "bottom","top"),
    ("vcc5",   "u8",     "solid", "", "bottom","top"),
    ("u8",     "usb4",   "solid", "", "bottom","top"),
    ("vcc5",   "u32",    "solid", "", "bottom","top"),
    ("u32",    "usb2",   "solid", "", "bottom","top"),
    ("vcc5",   "u33",    "solid", "", "bottom","top"),
    ("u33",    "usb3",   "solid", "", "bottom","top"),
]

def anchor_pt(nid, side):
    cx, cy, _, _, _ = NODES[nid]
    if side == "top":    return (cx, cy - H/2)
    if side == "bottom": return (cx, cy + H/2)
    if side == "left":   return (cx - W/2, cy)
    if side == "right":  return (cx + W/2, cy)
    return (cx, cy)

svg = []
svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="880" '
           'font-family="Consolas,SimHei,sans-serif" font-size="11">')
svg.append('<defs>'
           '<marker id="m" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
           '<path d="M0,0 L9,4.5 L0,9 z" fill="#2c3e50"/></marker>'
           '<marker id="md" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
           '<path d="M0,0 L9,4.5 L0,9 z" fill="#c0392b"/></marker>'
           '</defs>')
svg.append('<rect width="1180" height="880" fill="#ffffff"/>')
svg.append('<text x="20" y="26" font-size="17" font-weight="bold">'
           'MAIN_V0.3 电源树 (Power Tree) — 由 Protel2 网表自动解析</text>')

# edges
for src, tgt, style, label, sa, ta in EDGES:
    x1, y1 = anchor_pt(src, sa)
    x2, y2 = anchor_pt(tgt, ta)
    dash = ' stroke-dasharray="6,4" stroke="#c0392b"' if style == "dash" else ' stroke="#2c3e50"'
    mk = "md" if style == "dash" else "m"
    svg.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
               f'stroke-width="2.2"{dash} marker-end="url(#{mk})"/>')
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        svg.append(f'<text x="{mx:.0f}" y="{my-4:.0f}" font-size="10" fill="#c0392b" '
                   f'text-anchor="middle">{label}</text>')

# nodes
for nid, (cx, cy, title, sub, fill) in NODES.items():
    x, y = cx - W/2, cy - H/2
    svg.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{W}" height="{H}" rx="6" '
               f'fill="{fill}" stroke="#1b2631" stroke-width="1.2"/>')
    svg.append(f'<text x="{cx:.0f}" y="{cy-3:.0f}" font-size="12" font-weight="bold" '
               f'fill="#ffffff" text-anchor="middle">{title}</text>')
    svg.append(f'<text x="{cx:.0f}" y="{cy+12:.0f}" font-size="9" '
               f'fill="#fdfefe" text-anchor="middle">{sub}</text>')

# legend
lx, ly = 700, 60
svg.append('<rect x="%d" y="%d" width="460" height="92" rx="6" fill="#f4f6f7" stroke="#bdc3c7"/>' % (lx, ly))
svg.append('<text x="%d" y="%d" font-size="12" font-weight="bold" fill="#2c3e50">图例 / 说明</text>' % (lx+12, ly+20))
svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2c3e50" stroke-width="2.2" marker-end="url(#m)"/>' % (lx+12, ly+40, lx+52, ly+40))
svg.append('<text x="%d" y="%d" font-size="10" fill="#2c3e50">已确认路径（网表引脚-网络映射）</text>' % (lx+60, ly+43))
svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c0392b" stroke-width="2.2" stroke-dasharray="6,4" marker-end="url(#md)"/>' % (lx+12, ly+62, lx+52, ly+62))
svg.append('<text x="%d" y="%d" font-size="10" fill="#c0392b">待核对：CH224K 控制 OR-ing 栅极；U7 VIN 来自 VCC5V</text>' % (lx+60, ly+65))
svg.append('<text x="%d" y="%d" font-size="10" fill="#2c3e50">注：A_3V3 由 U1(NB680GD) 与 U7(SY8088) 双 buck 并联供电</text>' % (lx+12, ly+83))

svg.append('</svg>')

with open("power_tree.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
print("wrote power_tree.svg with", len(NODES), "nodes,", len(EDGES), "edges")
