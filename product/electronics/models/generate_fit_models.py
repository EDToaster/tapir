"""Tapir's original fit references, not vendor replicas. Dimensions in mm.

Use the environment pinned in mechanical/stack/requirements.lock. Coordinates
are component local, the KiCad STEP convention (+Y opposite PCB editor Y),
and z=0 is the carrier's component-side copper plane. No post-import transforms.
"""

import argparse
from pathlib import Path
from build123d import (
    Align, Box, Color, Compound, Cylinder, Plane, Pos, RectangleRounded,
    Sphere, export_step, extrude, loft,
)

ROOT = Path(__file__).resolve().parent
ZERO = (Align.CENTER, Align.CENTER, Align.MIN)
STAMP = "2026-11-21T00:00:00"


def box(x, y, z, w, d, h):
    return Pos(x, y, z) * Box(w, d, h, align=ZERO)


def cyl(x, y, z, r, h):
    return Pos(x, y, z) * Cylinder(r, h, align=ZERO)


def piece(shape, name, color):
    shape.label = name
    shape.color = Color(color)
    return shape


def cap():
    # Independently drawn, slightly tapered skirt and shallow finger dish.
    # The full plan bounding extent and 10.6 mm seated peak are fit datums;
    # draft, radii, crown, cavity and skirt bottom are visualization allowances.
    # Omit the two press-fit stems: this isn't mold tooling or a printable cap.
    shell = loft([
        Plane.XY.offset(6.65) * RectangleRounded(17.50, 16.50, 1.00),
        Plane.XY.offset(10.60) * RectangleRounded(15.25, 14.25, 1.60),
    ], ruled=True)
    shell -= box(0, 0, 6.2, 13.8, 12.6, 2.0)
    shell -= Pos(0, 0, 40.0) * Sphere(30.0)
    return piece(shell, "MBK_1U_independent_clearance_not_mold_geometry", "#718399")


def module():
    # Actual non-Sense Plus v1.1 plan artwork, centered about board outline.
    # Board editor offsets retained to 0.01 mm here. Z standoff 0.15 mm is
    # an allowance; the vendor CAD's nominal design board thickness is 1.60.
    z0 = 0.15
    top = z0 + 1.60
    pcb = Pos(0, 0, z0) * extrude(RectangleRounded(20.955, 17.78, 1.15), 1.60)
    lands = []
    main = [n * 2.54 for n in range(-3, 4)]
    plus = ([n * 2.54 + 1.27 for n in range(-3, 3)], [-6.35, -3.81, -1.27])
    for side, extra in zip((1, -1), plus):
        for x in main + extra:
            y = side * 8.89
            pcb -= cyl(x, y, z0 - 0.2, 0.3, 2.0)
        for x in main:
            y = side * 7.62
            pcb -= cyl(x, y, z0 - 0.2, 0.5, 2.0)
            ring = cyl(x, y, top, 0.70, 0.025) - cyl(x, y, top - 0.05, 0.50, 0.15)
            lands.append(ring)
        for x in extra:
            # The nine interstitial D11..D19 positions belong to Plus, not base.
            lands.append(box(x, side*8.40, z0-0.025, 0.65, 0.65, 0.025))
    for x, y in ((6.032, -1.27), (6.032, 1.27), (8.572, -1.27), (8.572, 1.27)):
        lands.append(cyl(x, y, z0 - 0.025, 1.143/2, 0.025))
    for y in (-1.00, 1.00):
        lands.append(box(-5.04, y, z0-0.025, 2.032, 1.016, 0.025))
    # Shell bounds from actual USB1 Fab rectangle; side heights estimated.
    # Internal cavity and tongue only show direction: do not certify a plug.
    shell = box((4.6355+11.9855)/2, 0, top, 7.35, 9.0, 3.40)
    shell -= box(10.1, 0, top+0.42, 4.8, 7.9, 2.55)
    parts = [
        piece(pcb, "Plus_PCB_23_positions_14_main_9_interstitial", "#243e35"),
        piece(Compound(children=lands), "Castellated_and_underside_contact_land_envelopes", "#c6a34b"),
        piece(shell, "USB1_shell_FFab_XY_approximate_Z", "#aec3c8"),
        piece(box(9.55, 0, top+1.48, 3.6, 6.5, 0.40), "USB1_tongue_schematic", "#37474f"),
        piece(box(-2.22, -0.635, top, 7.0, 7.0, 0.85), "U1_radio_package_envelope", "#242a30"),
        piece(box(-9.41, 1.80, top, 1.60, 3.20, 1.04), "ANT1_not_RF_keepout", "#d9cdaf"),
        piece(box(8.57, 5.715, top, 2.60, 1.60, 0.53), "K1_reset_envelope", "#777b7d"),
    ]
    return Compound(children=parts, label="XIAO_nRF52840_Plus_102010672_NONSENSE_FIT_ONLY")


def jst():
    # Derived from PH SMT side-entry datasheet and KiCad Fab outline; exact
    # variant is S2B-PH-SM4-TB(LF)(SN), never the narrower THT S2B-PH-K.
    # Shell front y=-4.40, rear signal tails reach y=+4.20. Housing and
    # reinforcement sections are simplified. No mating-connector model.
    body = box(0, -1.40, 0, 7.90, 6.0, 5.50)
    body -= box(0, -3.15, 0.75, 5.40, 4.0, 3.80)
    contacts = []
    for sign in (-1, 1):
        contacts += [
            box(sign, 2.90, 0, 0.50, 2.60, 0.25),
            box(sign, -2.55, 2.45, 0.5, 2.70, 0.5),
            box(sign*3.55, 2.40, 0, 0.80, 1.60, 0.32),
        ]
    return Compound(children=[
        piece(body, "PH_2way_side_entry_housing_fit", "#e9e2c9"),
        piece(Compound(children=contacts), "Simplified_tails_posts_tabs", "#abaea1"),
    ], label="JST_S2B_PH_SM4_TB_FIT_ONLY")


MODELS = {
    "MBK_1U_clearance_seated": cap,
    "XIAO_nRF52840_Plus_nonSense_fit": module,
    "JST_S2B_PH_SM4_TB_fit": jst,
}

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, make in MODELS.items():
        model = make()
        if not model.is_valid or not model.solids():
            raise ValueError(f"invalid model: {name}")
        if not export_step(model, args.out / f"{name}.step", timestamp=STAMP):
            raise IOError(name)
        print(name, model.bounding_box(), flush=True)
