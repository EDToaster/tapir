#!/usr/bin/python3
"""Write TmrHalf.pretty: this project's own land patterns plus unmodified KiCad 10.0.8 stock ones.

Own drawings (dimensions and sources are in ../README.md):
  SW_Gateron_LP_Magnetic_KS-33D  holes from the Gateron KS-33D drawing
  SOT-23-3_TMR2617S              SOT-23-3 for the MDT TMR2617S outline, short toe only on the row beside the switch hole
  SW_SPDT_CK_PCM12SMTR           C&K PCM12SMTR slide switch, from the C&K PCM series drawing
  Fiducial_1mm_Mask2mm           1 mm copper dot in a 2 mm solder-mask opening
  ProMicro_nRF52840_THT          2 x 12 header, 2.54 mm pitch, 15.24 mm row spacing
  PinHeader_1xNN_P2.54mm         in-line pads along +X
  MountingHole_M2_NPTH           2.2 mm hole with a 5 mm standoff keep-out

Stock footprints are copied byte for byte from the KiCad library that ships in
the kicad/kicad:10.0.8 image (CC BY-SA 4.0 with the KiCad library design exception).
Their 0.12 mm silkscreen strokes are widened to 0.15 mm when place_board.py puts them on the board.
Run inside that image; the committed library is normally used as is.
"""
from pathlib import Path
from design import ROOT, LIB

OUT = ROOT / f"{LIB}.pretty"
STOCK = Path("/usr/share/kicad/footprints")
COPIES = {
    "SOT-23": "Package_TO_SOT_SMD", "SSOP-24_5.3x8.2mm_P0.65mm": "Package_SO",
    "R_0603_1608Metric": "Resistor_SMD", "C_0603_1608Metric": "Capacitor_SMD",
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": "Connector_JST",
}
SILK_W = 0.15       # JLCPCB minimum silkscreen stroke


def font(size=0.8):
    return f"(effects (font (size {size} {size}) (thickness {round(size * 0.15, 3)})))"


def header(name, descr, attr, ref_at=(0, -2), val_at=(0, 2)):
    return (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "tmr_half_footprints")\n\t(layer "F.Cu")\n'
            f'\t(descr "{descr}")\n'
            f'\t(property "Reference" "REF**" (at {ref_at[0]} {ref_at[1]} 0) (layer "F.SilkS") (hide yes) {font()})\n'
            f'\t(property "Value" "{name}" (at {val_at[0]} {val_at[1]} 0) (layer "F.Fab") {font()})\n'
            f'\t(attr {attr})\n')


def line(a, b, layer, w=SILK_W):
    return (f'\t(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width {w}) (type solid)) (layer "{layer}"))\n')


def rect(x0, y0, x1, y1, layer, w=0.1):
    return (f'\t(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}"))\n')


def circle(r, layer, w=0.05, at=(0, 0)):
    return (f'\t(fp_circle (center {at[0]} {at[1]}) (end {at[0] + r} {at[1]}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}"))\n')


def text(s, x, y, layer, size=0.8, angle=0):
    return f'\t(fp_text user "{s}" (at {x} {y} {angle}) (layer "{layer}") {font(size)})\n'


def npth(x, y, d):
    return f'\t(pad "" np_thru_hole circle (at {x} {y}) (size {d} {d}) (drill {d}) (layers "*.Cu" "*.Mask"))\n'


def tht(n, x, y, pad=1.7, drill=1.0, square=False):
    return (f'\t(pad "{n}" thru_hole {"rect" if square else "circle"} (at {x} {y}) (size {pad} {pad}) (drill {drill})'
            f' (layers "*.Cu" "*.Mask") (remove_unused_layers no))\n')


def smd(n, x, y, w, h):
    return (f'\t(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Mask" "F.Paste")'
            f' (roundrect_rratio 0.25))\n')



END = "\t(embedded_fonts no)\n)\n"


def switch():
    # Gateron KS-33D drawing: centre hole 5.20, two 1.70 +/-0.05 holes at +/-5.08 on the
    # centre line, body 14.0 square. The magnet sits on the side opposite the light pipe,
    # which is the logo side of the switch. +Y is that side.
    s = header("SW_Gateron_LP_Magnetic_KS-33D", "Gateron low profile magnetic switch KS-33D, no electrical pins",
               "exclude_from_pos_files exclude_from_bom board_only", (0, -8), (0, 8))
    s += npth(0, 0, 5.2) + npth(-5.08, 0, 1.7) + npth(5.08, 0, 1.7)
    s += rect(-7, -7, 7, 7, "F.Fab") + rect(-7.1, -7.1, 7.1, 7.1, "F.CrtYd", 0.05)
    # Leave the switch seat free of ink; the orientation cue is outside the front courtyard.
    s += text("${REFERENCE}", 0, -2, "F.Fab", 0.8)
    return s + END


def sensor():
    # MDT TMR2617S-AAC datasheet figure 7 (drawing): body 2.95 x 1.65, lead span 2.80 +/-0.20,
    # pins 1 and 2 on 1.90 centres, lead width 0.30-0.49. KiCad SOT-23 convention: pins 1 and 2 at -X,
    # pin 3 at +X. The lead tips are 1.40 mm from the body centre (1.30 to 1.50 over the span tolerance).
    #   Pins 1 and 2 face the Gateron centre hole. Their pads end 1.60 mm from the body centre, which is
    #   2.80 mm from the switch centre, so the toe is 0.20 mm nominal (0.10 to 0.30). They cannot grow
    #   toward the hole without going under 0.30 mm of copper-to-hole clearance.
    #   Pin 3 faces away from the hole. Its pad runs out to 1.95 mm: toe 0.55 mm nominal (0.45 to 0.65).
    # All three pads start 0.50 mm from the body centre, so the heel side is unchanged. The footprint
    # origin is the body centre, which is what the placement file reports for this part.
    s = header("SOT-23-3_TMR2617S", "MDT TMR2617S SOT-23-3, short toe on the pin 1-2 row for placement beside the Gateron centre hole",
               "smd", (0, -2.4), (0, 2.4))
    s += line((-0.7, -1.6), (0.7, -1.6), "F.SilkS") + line((-0.7, 1.6), (0.7, 1.6), "F.SilkS")
    s += rect(-0.825, -1.475, 0.825, 1.475, "F.Fab") + circle(0.15, "F.Fab", 0.1, (-0.45, -0.95))
    s += rect(-1.77, -1.75, 2.2, 1.75, "F.CrtYd", 0.05) + text("${REFERENCE}", 0, 0, "F.Fab", 0.5, 90)
    s += smd(1, -1.05, -0.95, 1.1, 0.6) + smd(2, -1.05, 0.95, 1.1, 0.6) + smd(3, 1.225, 0, 1.45, 0.6)
    return s + END


def slide_switch():
    # C&K PCM series sheet I-44, "PC MOUNTING" view for PCM12SMTR (drawing). Origin is midway between the
    # two locating posts. Terminals are at -Y, the lever at +Y.
    #   terminal pads 0.7 x 1.5 at x = -2.25, +0.75, +2.25 (pad 2 is 0.75 right of centre, pad 1 3.0 left
    #   of pad 2, pad 3 1.5 right of pad 2); they span 1.0 to 2.5 from the post centre line
    #   four shell pads 1.0 x 0.8, inner edges 6.3 apart, 1.13 between the two rows
    #   two 0.9 mm holes 3.0 apart for the locating posts (0.8 mm posts)
    #   body 6.7 x 2.6, 1.4 high; lever 1.3 wide, 1.5 long, 1.5 travel
    # The drawing does not dimension the shell-pad rows against the post line. They are drawn symmetric
    # about it, and the body is 2.6 deep with the shell tabs at its two long edges, so +/-0.965 is used
    # (allowance: read from the drawing, not a stated dimension).
    s = header("SW_SPDT_CK_PCM12SMTR", "C&K PCM12SMTR SPDT slide switch, side actuated, drawn from the C&K PCM series sheet",
               "smd", (0, -3.6), (0, 3.9))
    for n, x in ((1, -2.25), (2, 0.75), (3, 2.25)):
        s += smd(n, x, -1.75, 0.7, 1.5)
    for x in (-3.65, 3.65):
        for y in (-0.965, 0.965):
            s += smd("MP", x, y, 1.0, 0.8)
    s += npth(-1.5, 0, 0.9) + npth(1.5, 0, 0.9)
    s += rect(-3.35, -1.3, 3.35, 1.3, "F.Fab") + rect(-1.4, 1.3, -0.1, 2.8, "F.Fab") + rect(0.1, 1.3, 1.4, 2.8, "F.Fab", 0.05)
    s += line((-2.85, 1.30), (2.85, 1.30), "F.SilkS")
    s += line((-1.5, -1.45), (0.0, -1.45), "F.SilkS")
    s += rect(-4.4, -2.75, 4.4, 3.05, "F.CrtYd", 0.05) + text("${REFERENCE}", 0, 0.6, "F.Fab", 0.6)
    return s + END


def fiducial():
    # 1 mm bare copper dot, 2 mm solder-mask opening, no paste. The pad clearance keeps the ground fill
    # out of the opening.
    s = header("Fiducial_1mm_Mask2mm", "Assembly fiducial, 1 mm copper in a 2 mm mask opening",
               "smd exclude_from_pos_files exclude_from_bom board_only", (0, -1.8), (0, 1.8))
    s += ('\t(pad "" smd circle (at 0 0) (size 1 1) (layers "F.Cu" "F.Mask") (solder_mask_margin 0.5) (clearance 0.5))\n')
    s += circle(1.0, "F.Fab", 0.1) + circle(1.25, "F.CrtYd")
    return s + END


def reverse_led():
    # KENTO KT-0603R datasheet p.2: 1.60 x 0.80 mm body, two 0.70 mm square lands,
    # 0.70 mm gap. Pin 1 anode, 2 cathode; marker at pin 2.
    s = header("LED_KENTO_KT-0603R", "KENTO KT-0603R red LED, manufacturer's 0603 land pattern", "smd")
    s += smd(1, -0.7, 0, 0.7, 0.7) + smd(2, 0.7, 0, 0.7, 0.7)
    s += line((1.28, -0.43), (1.28, 0.43), "F.SilkS")
    s += rect(-0.8, -0.4, 0.8, 0.4, "F.Fab") + rect(-1.3, -0.65, 1.45, 0.65, "F.CrtYd", 0.05)
    return s + END


def controller():
    # Origin at the centre of the 2 x 12 pad field. Pad 1 is top-left with the USB
    # connector at -Y, pads 13-24 run up the right column. The outline is the
    # 17.78 x 33.02 mm nice!nano v2 board, which extends one extra pin pitch past pad 1.
    s = header("ProMicro_nRF52840_THT", "Pro Micro format nRF52840 module (nice!nano v2 pinout), 2x12 pins, 15.24 mm rows",
               "through_hole exclude_from_pos_files", (0, -19.5), (0, 16.5))
    for i in range(12):
        y = round(-13.97 + 2.54 * i, 3)
        s += tht(i + 1, -7.62, y, square=i == 0) + tht(24 - i, 7.62, y)
    s += rect(-8.89, -17.78, 8.89, 15.24, "F.Fab") + rect(-4.47, -18.9, 4.47, -11.6, "F.Fab")
    s += rect(-9.15, -19.15, 9.15, 15.5, "F.CrtYd", 0.05)
    for x in (-8.89, 8.89):
        s += line((x, -17.55), (x, 15.24), "F.SilkS")
    s += line((-8.89, 15.24), (8.89, 15.24), "F.SilkS")
    s += line((-8.89, -17.55), (-4.47, -17.55), "F.SilkS") + line((4.47, -17.55), (8.89, -17.55), "F.SilkS")
    s += text("${REFERENCE}", 0, 0, "F.Fab", 1.0)
    return s + END


def pins(count):
    name = f"PinHeader_1x{count:02}_P2.54mm"
    s = header(name, f"1x{count} 2.54 mm pin header or probe pads, pads along +X", "through_hole exclude_from_pos_files",
               (0, -2.3), (0, 2.3))
    for i in range(count):
        s += tht(i + 1, round(2.54 * i, 2), 0, square=i == 0)
    x1 = round(2.54 * (count - 1) + 1.27, 2)
    s += rect(-1.27, -1.27, x1, 1.27, "F.Fab") + rect(-1.5, -1.5, round(x1 + 0.23, 2), 1.5, "F.CrtYd", 0.05)
    s += text("${REFERENCE}", round(x1 / 2 - 0.6, 2), 0, "F.Fab", 0.7)
    return name, s + END


def mount():
    s = header("MountingHole_M2_NPTH", "M2 clearance hole, non-plated, 5 mm keep-out for a standoff or screw head",
               "exclude_from_pos_files exclude_from_bom board_only", (0, -3.2), (0, 3.2))
    s += npth(0, 0, 2.2) + circle(2.5, "F.CrtYd") + circle(2.5, "B.CrtYd") + circle(2.5, "Cmts.User", 0.1)
    return s + END


def make():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.kicad_mod"):
        old.unlink()
    for name, family in COPIES.items():
        (OUT / f"{name}.kicad_mod").write_text((STOCK / f"{family}.pretty" / f"{name}.kicad_mod").read_text())
    own = {"SW_Gateron_LP_Magnetic_KS-33D": switch(), "SOT-23-3_TMR2617S": sensor(),
           "SW_SPDT_CK_PCM12SMTR": slide_switch(), "Fiducial_1mm_Mask2mm": fiducial(), "LED_KENTO_KT-0603R": reverse_led(),
           "ProMicro_nRF52840_THT": controller(), "MountingHole_M2_NPTH": mount(), **dict(pins(n) for n in (2, 10))}
    for name, body in own.items():
        (OUT / f"{name}.kicad_mod").write_text(body)
    print(f"{OUT.name}: {len(COPIES)} stock, {len(own)} own footprints")


if __name__ == "__main__":
    make()
