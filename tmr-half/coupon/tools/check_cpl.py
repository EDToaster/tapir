#!/usr/bin/python3
"""Fit the published JLC/EasyEDA pad centres to actual KiCad pads at CPL rotation.

Assembly convention assumption: 0° is the library drawing seen from the
assembly side, with counterclockwise rotation. The assembler preview remains
mandatory. Checks library datum, locating pegs and pad centres separately;
does not verify solder volume or registration on assembled hardware.
"""
import argparse
import csv
from itertools import permutations
import json
import math
from pathlib import Path

import pcbnew as k
from design import ROOT, STEM, REV

LIB = Path(__file__).with_name("cpl-library-pads.json")
MP = {"C295747": {"3", "4"}, "C221841": {"4"}}
PAD_LIMIT = 0.10
DATUM_LIMIT = 0.025


def rotate(x, y, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return c*x - s*y, s*x + c*y


def score(lib, ours, angle):
    err = 0.0
    for pad, points in lib.items():
        rotated = [rotate(x, y, angle) for x, y in points]
        err = max(err, min(max(math.dist(a, b) for a, b in zip(rotated, q))
                           for q in permutations(ours[pad])))
    return err


def verify(pcb, bom, cpl):
    fixture = json.loads(LIB.read_text())
    libdata = fixture["parts"]
    if libdata.keys() != fixture["origins_10mil"].keys():
        raise ValueError("Missing raw library origin")
    with bom.open(newline="") as f:
        parts = {r: row["LCSC Part #"] for row in csv.DictReader(f) for r in row["Designator"].split(",")}
    with cpl.open(newline="") as f:
        rows = list(csv.DictReader(f))
    poses = {row["Designator"]: row for row in rows}
    if len(rows) != len(poses) or set(parts) != set(poses):
        raise ValueError("CPL must contain exactly one placement per BOM reference")
    board = k.LoadBoard(str(pcb))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    worst_raw = worst_fit = worst_datum = worst_peg = 0.0
    errors = []
    for ref, lcsc in sorted(parts.items()):
        row, f = poses[ref], fps[ref]
        back = f.GetLayer() == k.B_Cu
        if row["Layer"] != ("Bottom" if back else "Top"):
            raise ValueError(f"{ref}: incorrect CPL side")
        x, y = (float(row[name].removesuffix("mm")) for name in ("Mid X", "Mid Y"))
        angle = float(row["Rotation"])
        if not all(math.isfinite(v) for v in (x, y, angle)):
            raise ValueError(f"{ref}: nonfinite CPL position or rotation")
        mirror = -1 if back else 1

        def relative(q):
            return (k.ToMM(q.x)-x)*mirror, -k.ToMM(q.y)-y

        holes = [relative(p.GetPosition()) for p in f.Pads() if p.GetAttribute() == k.PAD_ATTRIB_NPTH]
        ox, oy = fixture["origins_10mil"][lcsc]
        pegs = [((px-ox)*0.254, (oy-py)*0.254)
                for px, py in fixture["locating_holes_10mil"].get(lcsc, [])]
        if len(holes) != len(pegs):
            raise ValueError(f"{ref}: library peg count differs from board holes")
        datum = tuple(sum(axis)/len(pegs) for axis in zip(*pegs)) if pegs else (0.0, 0.0)
        datum_error = math.dist(relative(f.GetPosition()), rotate(*datum, angle))
        peg_error = score({"peg": pegs}, {"peg": holes}, angle) if pegs else 0.0
        ours, lib, adjusted = {}, {}, {}
        for pad in f.Pads():
            if pad.GetAttribute() == k.PAD_ATTRIB_SMD:
                ours.setdefault(pad.GetNumber(), []).append(relative(pad.GetPosition()))
        shift = fixture.get("land_pattern_allowances_mm", {}).get(lcsc, {}).get("pads", {})
        for n, px, py in libdata[lcsc]:
            key = "MP" if n in MP.get(lcsc, ()) else n
            lib.setdefault(key, []).append((px, py))
            dx, dy = shift.get(n, (0.0, 0.0))
            adjusted.setdefault(key, []).append((px+dx, py+dy))
        if {n: len(p) for n, p in ours.items()} != {n: len(p) for n, p in lib.items()}:
            raise ValueError(f"{ref} {lcsc}: library and board pad numbers/counts differ")
        raw, fit = score(lib, ours, angle), score(adjusted, ours, angle)
        worst_raw, worst_fit = max(worst_raw, raw), max(worst_fit, fit)
        worst_datum, worst_peg = max(worst_datum, datum_error), max(worst_peg, peg_error)
        best = min((score(adjusted, ours, a), a) for a in (0, 90, 180, 270))
        if fit > PAD_LIMIT or max(datum_error, peg_error) > DATUM_LIMIT:
            errors.append(ref)
        print(f"{ref:4} {lcsc:10} {angle:3g}° raw {raw:.3f}; residual {fit:.3f}; "
              f"datum {datum_error:.4f}; peg {peg_error:.4f} mm; best {best[1]:3g}° {best[0]:.3f} mm")
    print(f"CPL fit: {len(poses)} parts, {len(errors)} failed {errors}; max raw {worst_raw:.4f}, "
          f"residual {worst_fit:.4f} (limit {PAD_LIMIT:.3f}), datum {worst_datum:.4f}, "
          f"peg {worst_peg:.4f} mm (datum and pegs limit {DATUM_LIMIT:.3f} mm)")
    return bool(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    name = ROOT / "fab" / f"{STEM}-rev{REV}"
    parser.add_argument("--pcb", type=Path, default=ROOT / (STEM + ".kicad_pcb"))
    parser.add_argument("--bom", type=Path, default=Path(f"{name}-bom-jlc.csv"))
    parser.add_argument("--cpl", type=Path, default=Path(f"{name}-cpl-jlc.csv"))
    args = parser.parse_args()
    raise SystemExit(verify(args.pcb, args.bom, args.cpl))
