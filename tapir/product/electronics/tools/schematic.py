#!/usr/bin/env python3
"""Build the editable, single-sheet Tapir carrier schematics and their symbol libraries.

All coordinates below are in 50 mil grid units. Symbol-local Y is up, sheet Y is
down. The design manifest owns terminal numbering, net names and board UUIDs.
This program draws symbols and orthogonal wires, not an image of a circuit.
"""

import argparse
import hashlib
import json
import re
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = 1.27


def q(s):
    return json.dumps(str(s), ensure_ascii=False)


def uid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, s))


def n(grid):
    return f"{grid * G:.4f}".rstrip("0").rstrip(".") or "0"


def xy(x, y):
    return f"{n(x)} {n(y)}"


def effects(size=1.27, justify=None, hide=False, bold=False):
    return (f'(effects (font (size {size} {size})' + (' (bold yes)' if bold else '') + ')'
            + (f' (justify {justify})' if justify else '')
            + (' (hide yes)' if hide else '') + ')')


def prop(key, value, x, y, *, hide=False, justify=None, size=1.27):
    return f'(property {q(key)} {q(value)} (at {xy(x, y)} 0) {effects(size, justify, hide)})'


def stroke(w=0.254):
    return f'(stroke (width {w}) (type default))'


def line(*points, width=0.254):
    return ('(polyline (pts ' + ' '.join(f'(xy {xy(*p)})' for p in points)
            + f') {stroke(width)} (fill (type none)))')


def rect(x1, y1, x2, y2, fill="background", width=0.254):
    return (f'(rectangle (start {xy(x1, y1)}) (end {xy(x2, y2)}) {stroke(width)}'
            f' (fill (type {fill})))')


def circle(x, y, r):
    return f'(circle (center {xy(x, y)}) (radius {n(r)}) {stroke(0.22)} (fill (type none)))'


def nat(x):
    return [(int(s) if s.isdigit() else s) for s in re.split(r'(\d+)', str(x))]


def netpins(c):
    return {p["net"]: i for i, p in c["pins"].items() if p["net"]}


def pin_at(p, x, y):
    px, py, _, _ = p
    return x + px, y - py


class Symbol:
    """Geometry plus electrical pins, measured from the symbol's own origin."""
    def __init__(self, name, c, loc, graphics, pin_labels=True, field_y=-4):
        self.name, self.c, self.loc = name, c, loc
        self.draw, self.show, self.field_y = graphics, pin_labels, field_y
        if set(loc) != set(c["pins"]):
            raise ValueError(f'{c["ref"]}: lost or extra symbol pins')

    def render(self, lib, qualified):
        c = self.c
        prefix = re.sub(r'\d+$', '', c["ref"])
        virtual = c["ref"].startswith("#")
        s = [f'(symbol {q(lib + ":" + self.name if qualified else self.name)}',
             ' (power global)' if virtual else '',
             f' (pin_names (offset 0.75){"" if self.show else " (hide yes)"})',
             '' if self.show else ' (pin_numbers (hide yes))',
             ' (exclude_from_sim no) (in_bom yes) (on_board yes)',
             prop("Reference", prefix, 0, -self.field_y, hide=virtual),
             prop("Value", c["value"], 0, -self.field_y + 2),
             prop("Footprint", c["footprint"], 0, 0, hide=True),
             prop("Datasheet", "", 0, 0, hide=True),
             prop("Description", "", 0, 0, hide=True),
             f' (symbol {q(self.name + "_0_1")} ' + '\n'.join(self.draw) + ')',
             f' (symbol {q(self.name + "_1_1")}']
        for i, (x, y, angle, length) in self.loc.items():
            p = c["pins"][i]
            typ = p.get("type") or "passive"
            s.append(f'  (pin {typ} line (at {xy(x, y)} {angle}) (length {n(length)})'
                     f' (name {q(p["name"])} {effects(1.05)}) (number {q(i)} {effects(0.95)}))')
        return '\n'.join(s) + '))'


def standard(c, *, kind=None, left=None, top=None):
    ids = sorted(c["pins"], key=nat)
    name = re.sub(r'[^A-Za-z0-9_+.-]', '_', c["footprint"].split(':')[-1])
    if kind == "key":
        right = next(i for i in ids if i != left)
        loc = {left: (-4, 0, 0, 2), right: (4, 0, 180, 2)}
        draw = [circle(-1.6, 0, .35), circle(1.6, 0, .35), line((-1.4, .28), (1.6, 1.7))]
        return Symbol(name, c, loc, draw, False, -3.5)
    if kind == "diode":
        # Bar faces the row wire: the electrical cathode faces toward decreasing
        # local Y. Determine pad numbers from nets, never from pin order alone.
        bot = next(i for i in ids if i != top)
        if c["pins"][bot]["name"].upper() not in ("K", "CATHODE", "C", "KATHODE"):
            raise ValueError(f'{c["ref"]}: expected the cathode on the row')
        loc = {top: (0, 3, 270, 2), bot: (0, -3, 90, 2)}
        draw = [line((-1, 1), (1, 1), (0, -1), (-1, 1)), line((-1.15, -1), (1.15, -1))]
        return Symbol(name, c, loc, draw, False)
    if len(ids) == 2 and c["ref"].startswith(("R", "C")):
        if c["ref"].startswith("R"):
            draw = [rect(-2, -.75, 2, .75, "none")]
            length = 2
        else:
            draw = [line((-.31, -1.1), (-.31, 1.1)), line((.31, -1.1), (.31, 1.1))]
            length = 3.69
        if kind == "vertical":
            if c["ref"].startswith("R"):
                draw = [rect(-.75, -2, .75, 2, "none")]
            else:
                draw = [line((-1.1,-.31), (1.1,-.31)), line((-1.1,.31),(1.1,.31))]
            return Symbol(name, c, {ids[0]: (0, 4, 270, length), ids[1]: (0, -4, 90, length)},
                          draw, False)
        return Symbol(name, c, {ids[0]: (-4, 0, 0, length), ids[1]: (4, 0, 180, length)},
                      draw, False)
    if kind == "spdt":
        common = left
        throws = [i for i in ids if i != common]
        loc = {common: (-5, 0, 0, 3), throws[0]: (5, 2, 180, 3), throws[1]: (5, -2, 180, 3)}
        draw = [circle(-1.75, 0, .26), circle(1.75, 2, .26), circle(1.75, -2, .26),
                line((-1.54, .14), (1.51, 1.86))]
        return Symbol(name, c, loc, draw, False, -5)
    if len(ids) <= 6 and c["ref"].startswith(("J", "TP")):
        a, b = ([], ids) if kind=="battery" else (ids, [])
        hw, pitch = 7, 4
    else:
        a, b = ids[:(len(ids)+1)//2], ids[(len(ids)+1)//2:]
        hw, pitch = (12, 3) if len(ids) > 10 else (8, 4)
    h = (max(len(a), len(b))-1) * pitch / 2
    loc = {}
    for side, pins in ((-1, a), (1, b)):
        for k, i in enumerate(pins):
            loc[i] = (side * (hw+2), h-k*pitch, 0 if side < 0 else 180, 2)
    return Symbol(name, c, loc, [rect(-hw, h+2, hw, -h-2)], True, -h-4.25)


class Sheet:
    def __init__(self, hand, manifest):
        self.hand, self.manifest = hand, manifest
        self.name = f'tapir-{hand}'
        self.lib = "TapirCircuit"
        self.root = uid(f'{self.name}-root')
        self.libs, self.objects, self.placed = {}, [], set()
        self.serial = 0

    def ident(self):
        self.serial += 1
        return f'(uuid {uid(self.name + "/graphic/" + str(self.serial))})'

    def text(self, x, y, txt, size=1.45, bold=False):
        self.objects.append(f'(text {q(txt)} (exclude_from_sim no) (at {xy(x,y)} 0)'
                            f' {effects(size, "left", bold=bold)} {self.ident()})')

    def divider(self, x1, y1, x2, y2):
        self.objects.append(f'(polyline (pts (xy {xy(x1,y1)}) (xy {xy(x2,y2)}))'
                            f' {stroke(.18)} (fill (type none)) {self.ident()})')

    def wire(self, a, b):
        if a == b:
            return
        if a[0] != b[0] and a[1] != b[1]:
            raise ValueError(f'not orthogonal: {a} to {b}')
        self.objects.append(f'(wire (pts (xy {xy(*a)}) (xy {xy(*b)})) {stroke(0.19)} {self.ident()})')

    def junction(self, x, y):
        self.objects.append(f'(junction (at {xy(x,y)}) (diameter 0.7) (color 0 0 0 0) {self.ident()})')

    def label(self, net, x, y, angle=0):
        if net is None:
            self.objects.append(f'(no_connect (at {xy(x,y)}) {self.ident()})')
            return
        just = 'right' if angle in (180, 270) else 'left'
        self.objects.append(f'(global_label {q(net)} (shape passive) (at {xy(x,y)} {angle})'
                            f' {effects(1.0, just)} {self.ident()})')

    def place(self, c, s, x, y, *, fields=None, value=True):
        if c["ref"] in self.placed:
            raise ValueError(f'duplicate placement: {c["ref"]}')
        self.placed.add(c["ref"])
        # Same footprint may serve two components with different functions or
        # pin assignments (e.g., resistor values or connector interfaces).
        sig = s.render(self.lib, False)
        base = s.name
        if base in self.libs and self.libs[base].render(self.lib, False) != sig:
            s.name = base + "_" + hashlib.sha1(sig.encode()).hexdigest()[:7]
        self.libs[s.name] = s
        fx, fy = fields if fields else (x, y+s.field_y)
        props = [prop("Reference", c["ref"], fx, fy, size=1.2, hide=c["ref"].startswith("#")),
                 prop("Value", c["value"], fx, fy-1.9, size=1.13, hide=not value),
                 prop("Footprint", c["footprint"], x, y, hide=True),
                 prop("Datasheet", "", x, y, hide=True), prop("Description", "", x, y, hide=True)]
        pins = '\n'.join(f'(pin {q(i)} (uuid {uid(c["uuid"] + ":pin:" + i)}))' for i in s.loc)
        self.objects.append(f'(symbol (lib_id {q(self.lib + ":" + s.name)}) (at {xy(x,y)} 0)'
                            f' (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)'
                            f' (uuid {c["uuid"]})\n' + '\n'.join(props) + '\n' + pins
                            + f'\n(instances (project {q(self.name)} (path {q("/" + self.root)}'
                            f' (reference {q(c["ref"])}) (unit 1)))))')

    def labeled(self, c, x, y, *, s=None):
        s = s or standard(c)
        self.place(c, s, x, y)
        for i, p in s.loc.items():
            px, py = pin_at(p, x, y)
            direction = 1 if p[0] > 0 else -1
            net = c["pins"][i]["net"]
            dx = px + (3*direction if net else 0)
            self.wire((px,py), (dx,py))
            self.label(net, dx, py, 0 if direction > 0 else 180)

    def flag(self, index, x, y):
        """Virtual source annotation, used only at the external supply entry."""
        ref = f"#FLG0{index}"
        c = dict(ref=ref, value="PWR_FLAG", footprint="", uuid=uid(self.name+"/"+ref),
                 pins={"1": dict(name="", type="power_out")})
        s = Symbol("PWR_FLAG", c, {"1": (0,0,90,0)},
                   [line((0,0),(0,1),(-.8,1.5),(0,2),(.8,1.5),(0,1))], False)
        self.place(c, s, x, y, fields=(x,y-1.8))

    def render(self, directory):
        title = "Tapir / " + self.hand.title() + " carrier"
        missing = {c["ref"] for c in self.manifest["components"]} - self.placed
        if missing:
            raise ValueError(f'unplaced: {missing}')
        embeds = '\n'.join(s.render(self.lib, True) for s in self.libs.values())
        libs = '\n'.join(s.render(self.lib, False) for s in self.libs.values())
        sch = (f'(kicad_sch (version 20260306) (generator "tapir_schematic")'
               f' (uuid {self.root}) (paper "A3")\n'
               f'(title_block (title {q(title)}) (rev "A") (company "Tapir")'
               ' (comment 1 "Carrier circuit; onboard module internals not repeated.")'
               ' (comment 2 "Engineering prototype / not released for manufacture"))\n'
               f'(lib_symbols\n{embeds})\n' + '\n'.join(self.objects)
               + '\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no))\n')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (self.name + ".kicad_sch")).write_text(sch)
        (directory / (self.lib + ".kicad_sym")).write_text(
            '(kicad_symbol_lib (version 20251024) (generator "tapir_schematic")\n' + libs + ')\n')
        (directory / 'sym-lib-table').write_text('(sym_lib_table (version 7)\n'
            f' (lib (name {q(self.lib)}) (type "KiCad") (uri "${{KIPRJMOD}}/{self.lib}.kicad_sym")'
            ' (options "") (descr "Tapir carrier symbols")))\n')


def matrix(sh, parts):
    """Discover actual branches and conductors from shared nets; omit empty cells."""
    switches = [c for c in parts if any(re.fullmatch("COL[0-5]", net) for net in netpins(c))
                and len(c["pins"]) == 2]
    diodes = [c for c in parts if c["ref"].startswith("D")]
    cells, colnets, rownets = {}, {}, {}
    for sw in switches:
        sn = netpins(sw)
        colnet, = (a for a in sn if re.fullmatch("COL[0-5]", a))
        mid, = set(sn) - {colnet}
        d, = (d for d in diodes if mid in netpins(d))
        dn = netpins(d)
        rownet, = set(dn) - {mid}
        if not re.fullmatch("ROW[0-3]", rownet):
            raise ValueError(f'{d["ref"]}: expected a row on cathode, found {rownet}')
        r, c = int(rownet[-1]), int(colnet[-1])
        if (r,c) in cells:
            raise ValueError(f'double-wired intersection {r},{c}')
        cells[r,c] = sw,d,mid
        colnets[c], rownets[r] = colnet,rownet
    if len(cells) != (24 if sh.hand=="left" else 21) or len(diodes) != len(cells):
        raise ValueError(f'{sh.hand}: expected each switch to have one diode; saw {len(cells)}')
    sh.text(13, 14, "01    KEY MATRIX", 2.30, True)
    sh.text(13, 19, "Column → contact → diode anode. The cathode bar returns to the row.", 1.28)
    for col, net in sorted(colnets.items()):
        x, yprev = 22+31*col, 26
        sh.label(net,x,yprev)
        for r in sorted(r for r,c in cells if c==col):
            y = 36+24*r
            sh.wire((x,yprev), (x,y))
            if yprev != 26:
                sh.junction(x,yprev)
            yprev = y
    for r, net in sorted(rownets.items()):
        y, xprev = 36+24*r+13, 17
        sh.label(net,xprev,y,180)
        for c in sorted(c for rr,c in cells if rr==r):
            x = 22+31*c+14
            sh.wire((xprev,y), (x,y))
            if xprev != 17:
                sh.junction(xprev,y)
            xprev = x
    for (r,c), (sw,d,mid) in sorted(cells.items()):
        x, y = 22+31*c, 36+24*r
        s = standard(sw,kind="key",left=netpins(sw)[colnets[c]])
        diode = standard(d,kind="diode",top=netpins(d)[mid])
        sh.place(sw,s,x+7,y,value=False)
        sh.place(d,diode,x+14,y+7,fields=(x+18,y+7),value=False)
        sh.wire((x,y),(x+3,y))
        sh.wire((x+11,y),(x+14,y))
        sh.label(mid,x+14,y)
        sh.wire((x+14,y),(x+14,y+4))
        sh.wire((x+14,y+10),(x+14,y+13))
    sh.text(13, 127, "ROW3  /  COL0–2: mouse controls. COL3–5: typing thumbs." if sh.hand=="left"
            else "ROW3  /  COL3–5: typing thumbs. COL0–2: intentionally empty. Right firmware reverses column order.", 1.25)
    return cells


def draw(sh):
    parts = sh.manifest["components"]
    matrix(sh, parts)
    sh.divider(204,10,204,130)
    sh.divider(11,131,320,131)
    sh.text(210, 14, "02    CONTROLLER & RADIO", 2.30, True)
    sh.text(210, 19, "Seeed XIAO nRF52840 Plus / non-Sense", 1.30)
    sh.text(210, 24, "USB-C, Li-ion charger and 3.3 V regulation are on the module.", 1.20)
    module = max(parts, key=lambda c: len(c["pins"]))
    sh.labeled(module, 263, 78)
    sh.text(210, 114, "NC markers designate unused carrier lands, not missing module features.", 1.20)
    sh.text(210, 119, "The USB port can power the module even when S1 disconnects the cell.", 1.20)
    support(sh, [c for c in parts if c["ref"] not in sh.placed])


def support(sh, remaining):
    """Draw the battery path, load switch/decoupling, and open-collector host bus."""
    p = {c["ref"]: c for c in remaining}
    sh.text(13, 139, "03    BATTERY DISCONNECT", 2.10, True)
    sh.text(13, 144, "Protected single cell / polarized, side-entry JST-PH.", 1.20)
    j = standard(p["J1"], kind="battery")
    sh.place(p["J1"],j,27,167)
    s = standard(p["S1"], kind="spdt", left="2")
    sh.place(p["S1"],s,68,163)
    sh.wire((36,163),(48,163)); sh.wire((48,163),(63,163))
    sh.wire((48,163),(48,157)); sh.label("CELL_PLUS",48,157)
    sh.junction(48,163)
    sh.wire((36,167),(42,167)); sh.wire((42,167),(42,177))
    sh.wire((42,177),(50,177)); sh.wire((50,177),(54,177))
    sh.flag(1,50,177); sh.junction(50,177); sh.label("GND",54,177)
    sh.label(None,36,171); sh.label(None,73,165)
    sh.wire((73,161),(81,161)); sh.wire((81,161),(86,161))
    sh.flag(2,81,161); sh.junction(81,161); sh.label("VBAT_SW",86,161)
    sh.text(13, 187, "J1 pin 1 = battery positive; pin 2 = return. Verify actual pack polarity.", 1.17)
    sh.text(13, 192, "S1 opens only the cell. Flags identify the pack return and switched feed", 1.17)
    sh.text(13, 196, "for ERC; they do not model charging, cell protection or source isolation.", 1.17)
    sh.text(13, 208, "ASSEMBLY / INSPECTION", 1.50, True)
    sh.text(13, 213, "Typing contacts: CPG135001D01. Diodes: 1N4148WS-7-F, band = K / pad 1 / row.", 1.18)
    sh.text(13, 217, "Confirm all joins with the native netlist. Charge and radio performance require bench verification.", 1.18)
    if sh.hand=="left":
        sh.divider(108,134,108,199)
        sh.text(115,139,"04    LEFT CONTROL BANK",2.10,True)
        sh.text(115,147,"SW22–SW24 are independent PTS810 tactile controls, not remapped typing keys.",1.35)
        sh.text(115,155,"SW22 / D22   →   ROW3 : COL0      Left click / drag while held",1.4)
        sh.text(115,162,"SW23 / D23   →   ROW3 : COL1      Scroll mode while held",1.4)
        sh.text(115,169,"SW24 / D24   →   ROW3 : COL2      Right click",1.4)
        sh.text(115,181,"Firmware assigns click and held-scroll behaviors; this sheet defines the electrical positions.",1.22)
        return
    sh.divider(106,134,106,200); sh.divider(207,134,207,196)
    sh.text(111,139,"04    SWITCHED POINTER SUPPLY",2.10,True)
    sh.text(111,144,"U1 supplies 3V3. R3 defaults the load switch to off.",1.20)
    # All geometry below is connected with real wires. Explicit pad numbering
    # is intentional: exported XML vs manifest validation catches stale wiring.
    u = Symbol("TPS22918",p["U2"],
               {"1":(-10,4,0,2),"2":(-10,-4,0,2),"3":(-10,0,0,2),
                "4":(10,-4,180,2),"5":(10,0,180,2),"6":(10,4,180,2)},
               [rect(-8,6,8,-6)], True, -8)
    sh.place(p["U2"],u,158,164)
    for ref,x,y in (("C1",120,177),("R3",136,177),("C2",185,177)):
        sh.place(p[ref],standard(p[ref],kind="vertical"),x,y,fields=(x+4.4,y+1))
    sh.label("3V3",115,160,180); sh.wire((115,160),(120,160)); sh.wire((120,160),(148,160))
    sh.wire((120,160),(120,173)); sh.junction(120,160)
    sh.label("PTR_EN",129,164,180); sh.wire((129,164),(136,164)); sh.wire((136,164),(148,164))
    sh.wire((136,164),(136,173)); sh.junction(136,164)
    sh.wire((148,168),(145,168)); sh.wire((145,168),(145,189))
    sh.label(None,168,168)
    sh.wire((168,160),(176,160)); sh.wire((176,160),(185,160)); sh.wire((185,160),(193,160))
    sh.wire((168,164),(176,164)); sh.wire((176,164),(176,160)); sh.junction(176,160)
    sh.wire((185,160),(185,173)); sh.junction(185,160); sh.label("PTR_3V3",193,160)
    sh.label("GND",115,189,180)
    for a,b in zip((115,120,136,145),(120,136,145,185)):
        sh.wire((a,189),(b,189))
    for x in (120,136,185):
        sh.wire((x,181),(x,189))
    for x in (120,136,145):
        sh.junction(x,189)
    sh.text(111,196,"CT left open; QOD tied to VOUT for output discharge.",1.17)
    sh.text(212,139,"05    PS/2 HOST HARNESS",2.10,True)
    sh.text(212,144,"Pull up CLK and DATA only to the switched pointer rail.",1.20)
    j = standard(p["J2"])
    sh.place(p["J2"],j,301,175)
    sh.label("PTR_3V3",232,151,180)
    for ref,x in (("R1",239),("R2",257)):
        sh.place(p[ref],standard(p[ref],kind="vertical"),x,160,fields=(x+4.5,161))
        sh.wire((x,151),(x,156))
    sh.wire((232,151),(239,151)); sh.wire((239,151),(257,151)); sh.junction(239,151)
    for ref,x,y,net in (("R1",239,171,"PS2_DATA"),("R2",257,175,"PS2_CLK")):
        sh.wire((x,164),(x,y)); sh.wire((224,y),(x,y)); sh.wire((x,y),(292,y))
        sh.junction(x,y); sh.label(net,224,y,180)
    for y,net in ((167,"GND"),(179,"PS2_RST"),(183,"PTR_3V3")):
        sh.label(net,279,y,180); sh.wire((279,y),(292,y))
    sh.text(212,191,"J2 → driver Method 1 castellations 1–5. RESET is active high.",1.17)
    sh.text(212,195,"Do not copy this order to driver FFC pads or the sensor flex.",1.17)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hands", nargs="*", default=["left","right"])
    ap.add_argument("--root", default=ROOT, type=Path)
    args = ap.parse_args()
    for hand in args.hands:
        if hand not in ("left","right"):
            ap.error("hand must be left or right")
        manifest = json.loads((args.root / "build" / hand / "design.json").read_text())
        sheet = Sheet(hand, manifest)
        draw(sheet)
        sheet.render(args.root / hand)
        print(f"{sheet.name}: {len(manifest['components'])} components, "
              f"{sum(r.startswith('#') for r in sheet.placed)} ERC supply markers, "
              f"{len(sheet.libs)} local symbols")


if __name__ == "__main__":
    main()
