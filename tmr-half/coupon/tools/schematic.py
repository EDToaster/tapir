#!/usr/bin/env python3
"""Draw the coupon schematic from the design manifest.

Coordinates are 50 mil grid units. Symbol-local Y is up, sheet Y is down. Every
pin ends in a short wire and a net label, so a net is read by matching names
between blocks. The manifest owns pin numbers and nets; check_schematic.py
exports KiCad's netlist and compares it with the manifest.
"""
import hashlib
import json
import re
import uuid

from design import ROOT, STEM, LIB, REV, KEYS, circuit

G = 1.27
SYMLIB = "TmrHalfSymbols"


def q(s):
    return json.dumps(str(s), ensure_ascii=False)


def uid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "tmr-half-coupon/sch/" + s))


def n(grid):
    return f"{grid * G:.4f}".rstrip("0").rstrip(".") or "0"


def xy(x, y):
    return f"{n(x)} {n(y)}"


def effects(size=1.27, justify=None, hide=False, bold=False):
    return (f'(effects (font (size {size} {size})' + (' (bold yes)' if bold else '') + ')'
            + (f' (justify {justify})' if justify else '') + (' (hide yes)' if hide else '') + ')')


def prop(key, value, x, y, *, hide=False, justify=None, size=1.27):
    return f'(property {q(key)} {q(value)} (at {xy(x, y)} 0) {effects(size, justify, hide)})'


def stroke(w=0.254):
    return f'(stroke (width {w}) (type default))'


def line(*points, width=0.254):
    return '(polyline (pts ' + ' '.join(f'(xy {xy(*p)})' for p in points) + f') {stroke(width)} (fill (type none)))'


def rect(x1, y1, x2, y2, fill="background"):
    return f'(rectangle (start {xy(x1, y1)}) (end {xy(x2, y2)}) {stroke()} (fill (type {fill})))'


class Symbol:
    """Graphics plus pins, measured from the symbol origin. loc: pin id -> (x, y, angle, length)."""
    def __init__(self, name, c, loc, graphics, pin_labels=True, top=4.0):
        self.name, self.c, self.loc, self.draw, self.show, self.top = name, c, loc, graphics, pin_labels, top
        if set(loc) != set(c["pins"]):
            raise ValueError(f'{c["ref"]}: symbol pins {sorted(loc)} differ from manifest {sorted(c["pins"])}')

    def render(self, qualified):
        c, virtual = self.c, self.c["ref"].startswith("#")
        s = [f'(symbol {q(SYMLIB + ":" + self.name if qualified else self.name)}',
             ' (power global)' if virtual else '',
             f' (pin_names (offset 0.75){"" if self.show else " (hide yes)"})',
             '' if self.show else ' (pin_numbers (hide yes))',
             ' (exclude_from_sim no) (in_bom yes) (on_board yes)',
             prop("Reference", re.sub(r'\d+$', '', c["ref"]), 0, -self.top, hide=virtual),
             prop("Value", c["value"], 0, -self.top - 2),
             prop("Footprint", c["footprint"], 0, 0, hide=True),
             prop("Datasheet", "", 0, 0, hide=True), prop("Description", c.get("description", ""), 0, 0, hide=True),
             f' (symbol {q(self.name + "_0_1")} ' + '\n'.join(self.draw) + ')',
             f' (symbol {q(self.name + "_1_1")}']
        for i, (x, y, angle, length) in self.loc.items():
            p = c["pins"][i]
            s.append(f'  (pin {p["type"]} line (at {xy(x, y)} {angle}) (length {n(length)})'
                     f' (name {q(p["name"])} {effects(1.05)}) (number {q(i)} {effects(0.95)}))')
        return '\n'.join(s) + '))'


def safe(name):
    return re.sub(r'[^A-Za-z0-9_+.-]', '_', name)


def passive(c):
    if c["ref"].startswith("R"):
        draw, length = [rect(-2, -.75, 2, .75, "none")], 2
    else:
        draw, length = [line((-.31, -1.1), (-.31, 1.1)), line((.31, -1.1), (.31, 1.1))], 3.69
    return Symbol(c["ref"][0] + "_0603", c, {"1": (-4, 0, 0, length), "2": (4, 0, 180, length)}, draw, False)


def box(c, left, right, hw=8, pitch=2, name=None):
    """Rectangle with named pins. left/right list pad numbers top to bottom; None leaves a gap."""
    rows = max(len(left), len(right)); h = -(-(rows - 1) * pitch // 2); low = h - (rows - 1) * pitch
    loc = {}
    for side, pins in ((-1, left), (1, right)):
        for k, i in enumerate(pins):
            if i is not None:
                loc[str(i)] = (side * (hw + 2), h - k * pitch, 0 if side < 0 else 180, 2)
    return Symbol(safe(name or c["value"]), c, loc, [rect(-hw, h + 1.5, hw, low - 1.5)], True, h + 3.4)


class Sheet:
    def __init__(self, manifest):
        self.manifest, self.root = manifest, uid("root")
        self.libs, self.objects, self.placed, self.serial, self.flags = {}, [], set(), 0, 0

    def ident(self):
        self.serial += 1
        return f'(uuid {uid("graphic/" + str(self.serial))})'

    def text(self, x, y, txt, size=1.3, bold=False):
        self.objects.append(f'(text {q(txt)} (exclude_from_sim no) (at {xy(x, y)} 0)'
                            f' {effects(size, "left", bold=bold)} {self.ident()})')

    def divider(self, x1, y1, x2, y2):
        self.objects.append(f'(polyline (pts (xy {xy(x1, y1)}) (xy {xy(x2, y2)})) {stroke(.18)}'
                            f' (fill (type none)) {self.ident()})')

    def wire(self, a, b):
        self.objects.append(f'(wire (pts (xy {xy(*a)}) (xy {xy(*b)})) {stroke(0.19)} {self.ident()})')

    def label(self, net, x, y, angle=0):
        if net is None:
            self.objects.append(f'(no_connect (at {xy(x, y)}) {self.ident()})')
            return
        just = 'right' if angle == 180 else 'left'
        self.objects.append(f'(global_label {q(net)} (shape passive) (at {xy(x, y)} {angle})'
                            f' {effects(1.0, just)} {self.ident()})')

    def place(self, c, s, x, y, stub=2):
        if c["ref"] in self.placed:
            raise ValueError("duplicate placement: " + c["ref"])
        self.placed.add(c["ref"])
        sig = s.render(False); base = s.name
        if base in self.libs and self.libs[base].render(False) != sig:
            s.name = base + "_" + hashlib.sha1(sig.encode()).hexdigest()[:6]
        self.libs[s.name] = s
        virtual = c["ref"].startswith("#")
        if len(s.loc) == 2 and not s.show:      # passives: "R5  10R" on one line above the body
            fields = [prop("Reference", c["ref"], x - .4, y - 2.1, size=1.1, justify="right"),
                      prop("Value", c["value"], x + .4, y - 2.1, size=1.1, justify="left")]
        else:
            fields = [prop("Reference", c["ref"], x, y - s.top - 1.8, size=1.2, hide=virtual),
                      prop("Value", c["value"], x, y - s.top, size=1.1, hide=virtual)]
        fields += [prop("Footprint", c["footprint"], x, y, hide=True), prop("Datasheet", "", x, y, hide=True),
                   prop("Description", c.get("description", ""), x, y, hide=True)]
        for key in ("mpn", "lcsc"):
            if c.get(key):
                fields.append(prop("MPN" if key == "mpn" else "LCSC", c[key], x, y, hide=True))
        pins = '\n'.join(f'(pin {q(i)} (uuid {uid(c["ref"] + ":pin:" + i)}))' for i in s.loc)
        dnp = "yes" if c.get("dnp") else "no"
        self.objects.append(
            f'(symbol (lib_id {q(SYMLIB + ":" + s.name)}) (at {xy(x, y)} 0) (unit 1) (exclude_from_sim no)'
            f' (in_bom yes) (on_board yes) (dnp {dnp}) (uuid {c["uuid"]})\n' + '\n'.join(fields) + '\n' + pins
            + f'\n(instances (project {q(STEM)} (path {q("/" + self.root)} (reference {q(c["ref"])}) (unit 1)))))')
        for i, (px, py, _, _) in s.loc.items():
            if virtual:
                continue
            ax, ay = x + px, y - py; d = 1 if px > 0 else -1; net = c["pins"][i]["net"]
            if net is None:
                self.label(None, ax, ay)
            else:
                self.wire((ax, ay), (ax + stub * d, ay)); self.label(net, ax + stub * d, ay, 0 if d > 0 else 180)

    def flag(self, net, x, y):
        """Tell ERC that a net is a supply even though no pin on this sheet is typed as its source."""
        self.flags += 1; ref = f"#FLG0{self.flags}"
        c = dict(ref=ref, value="PWR_FLAG", footprint="", uuid=uid(ref), pins={"1": dict(name="pwr", type="power_out", net=net)})
        s = Symbol("PWR_FLAG", c, {"1": (0, 0, 90, 0)}, [line((0, 0), (0, 1), (-.8, 1.5), (0, 2), (.8, 1.5), (0, 1))], False, 3)
        self.place(c, s, x, y)
        self.wire((x, y), (x + 3, y)); self.label(net, x + 3, y)

    def render(self, directory):
        missing = {c["ref"] for c in self.manifest["components"]} - self.placed
        if missing:
            raise ValueError(f"unplaced: {sorted(missing)}")
        embeds = '\n'.join(s.render(True) for s in self.libs.values())
        libs = '\n'.join(s.render(False) for s in self.libs.values())
        sch = (f'(kicad_sch (version 20260306) (generator "tmr_half_schematic") (uuid {self.root}) (paper "A3")\n'
               f'(title_block (title {q(self.manifest["title"])}) (rev {q(REV)}) (company "Tapir / tmr-half")'
               ' (comment 1 "Six-key analog readout test board for TMR2617S sensors")'
               ' (comment 2 "Engineering prototype. Not ordered until the owner approves."))\n'
               f'(lib_symbols\n{embeds})\n' + '\n'.join(self.objects)
               + '\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no))\n')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (STEM + ".kicad_sch")).write_text(sch)
        (directory / (SYMLIB + ".kicad_sym")).write_text(
            '(kicad_symbol_lib (version 20251024) (generator "tmr_half_schematic")\n' + libs + ')\n')
        (directory / 'sym-lib-table').write_text(
            f'(sym_lib_table (version 7)\n (lib (name {q(SYMLIB)}) (type "KiCad") (uri "${{KIPRJMOD}}/{SYMLIB}.kicad_sym")'
            ' (options "") (descr "TMR half coupon symbols")))\n')


def draw(sh):
    p = {c["ref"]: c for c in sh.manifest["components"]}
    T = lambda x, y, s, size=1.2: sh.text(x, y, s, size)
    H = lambda x, y, s: sh.text(x, y, s, 2.1, True)

    H(12, 13, "01    CONTROLLER")
    T(12, 18, "nice!nano v2 or pin-compatible nRF52840 clone, hand-fitted. Pads are numbered like a DIP:")
    T(12, 21, "1-12 down the left side, 13-24 up the right side, USB connector at the top.")
    sh.place(p["A1"], box(p["A1"], list(range(1, 13)), list(range(24, 12, -1)), hw=12, pitch=3, name="nice_nano_v2"), 56, 48)
    T(12, 72, "B+ is the module's battery input (charger on the module). VCC is its 3.3 V regulator output.")

    sh.divider(104, 9, 104, 78)
    H(108, 13, "02    SENSOR CELLS  (one per key)")
    T(108, 18, "TMR2617S: pin 1 supply, pin 2 analog output, pin 3 ground. Output falls as the magnet approaches (to be measured).")
    T(108, 21, "Rail A keys carry the datasheet 100 nF bypass, rail B keys 10 nF. The 100 pF output capacitor is fitted on K2 and K5 only.")
    for k in KEYS:
        i = k["n"]; x, y = 140 + 66 * k["col"], 33 + 26 * k["row"]
        sh.place(p[f"U{i}"], box(p[f"U{i}"], [1, 3], [2, None], hw=7, name="TMR2617S"), x, y)
        sh.text(x - 22, y - 5, f"K{i}", 1.6, True)
        sh.place(p[f"C{i}"], passive(p[f"C{i}"]), x, y + 8)
        sh.place(p[f"C{10 + i}"], passive(p[f"C{10 + i}"]), x, y + 13)

    sh.divider(11, 79, 320, 79)
    H(12, 84, "03    ANALOG MULTIPLEXERS")
    T(12, 89, "S0-S3 pick one of 16 inputs and connect it to COM. Both chips share the select lines, so one")
    T(12, 92, "address reads a rail A key and a rail B key together. Keys are on I1, I3, I5; I7 reads the rail. Other inputs are grounded.")
    for ref, x in (("U7", 50), ("U8", 142)):
        left = [9, 8, 7, 6, 5, 4, 3, 2, 23, 22, 21, 20, 19, 18, 17, 16]          # I0..I15
        right = [1, None, 24, 12, None, 10, 11, 14, 13, None, 15] + [None] * 5   # COM, VCC, GND, S0..S3, E
        sh.place(p[ref], box(p[ref], left, right, hw=9, pitch=3, name="CD74HC4067"), x, 123)
    sh.place(p["C7"], passive(p["C7"]), 84, 137); sh.place(p["C8"], passive(p["C8"]), 176, 137)
    T(72, 131, "U7 bypass"); T(164, 131, "U8 bypass")

    sh.divider(204, 79, 204, 152)
    H(208, 84, "04    SENSOR RAIL SWITCHES")
    T(208, 89, "P-channel MOSFET per rail. Gate pulled low = rail on, so the sensors are powered")
    T(208, 92, "until firmware drives PWR_x_N high. The 10 ohm resistor lets a meter read rail current.")
    for i, (rail, y) in enumerate((("A", 104), ("B", 130)), 1):
        sh.text(208, y - 6, f"RAIL {rail}", 1.5, True)
        sh.place(p[f"Q{i}"], box(p[f"Q{i}"], [1, None], [2, 3], hw=6, name="AO3401A"), 226, y)
        for ref, x, yy in ((f"R{i}", 264, y - 3), (f"R{i + 2}", 264, y + 3), (f"R{i + 4}", 264, y + 9),
                           (f"R{i + 6}", 302, y - 3), (f"R{i + 8}", 302, y + 3), (f"C{i + 16}", 302, y + 9)):
            sh.place(p[ref], passive(p[ref]), x, yy)
    T(208, 147, "MON_x = half the rail voltage, read on mux input I7 to watch the rail settle after power-up.")

    sh.divider(11, 152, 320, 152)
    H(12, 157, "05    ADC INPUTS AND SUPPORT")
    T(12, 162, "R11/R12 are 0 ohm links and C19/C20 are empty pads, so an RC filter can be tried without a new board.")
    for ref, x, y in (("R11", 30, 171), ("C19", 68, 171), ("R13", 108, 171), ("R12", 30, 178), ("C20", 68, 178), ("C9", 108, 178)):
        sh.place(p[ref], passive(p[ref]), x, y)
    for net, x in (("GND", 140), ("VS_A", 158), ("VS_B", 176), ("BAT_SW", 194)):
        sh.flag(net, x, 176)
    T(138, 170, "ERC supply markers (no part)")

    sh.divider(11, 186, 320, 186)
    H(12, 191, "06    BATTERY, RESET, DEBUG")
    T(12, 196, "Optional 1-cell LiPo. Q3 blocks reverse battery power without USB. D1 lights on a reversed cell with S1 open.")
    T(12, 199, "Still check pack polarity with a meter before plugging in: Q3 does not protect a reversed cell while USB is charging.")
    sh.place(p["J1"], box(p["J1"], [], [1, 2, "MP"], hw=5, name="JST_PH_2"), 24, 211)
    sh.place(p["Q3"], box(p["Q3"], [3, None], [2, 1], hw=6, name="AO3401A"), 62, 211)
    sh.place(p["R14"], passive(p["R14"]), 96, 211)
    sh.place(p["S1"], box(p["S1"], [2, None, None], [1, 3, "MP"], hw=6, name="PCM12SMTR"), 134, 211)
    sh.place(p["J2"], box(p["J2"], [], [1, 2], hw=4, name="Pads_1x02"), 172, 211)
    sh.place(p["J3"], box(p["J3"], [1, 2, 3, 4, 5], [6, 7, 8, 9, 10], hw=10, name="Header_1x10"), 224, 211)
    sh.place(p["R15"], passive(p["R15"]), 266, 211)
    sh.place(p["D1"], box(p["D1"], [2], [1], hw=5, name="Reverse_Battery_LED"), 302, 211)
    T(160, 221, "J2: short to reset"); T(206, 221, "J3: probe points / optional header")


def main():
    manifest = circuit()
    sheet = Sheet(manifest); draw(sheet)
    for d in (ROOT, ROOT / "build"):
        sheet.render(d)
    print(f"{STEM}.kicad_sch: {len(manifest['components'])} components, {sheet.flags} supply markers, {len(sheet.libs)} symbols")


if __name__ == "__main__":
    main()
