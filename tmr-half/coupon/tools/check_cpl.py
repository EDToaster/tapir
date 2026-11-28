#!/usr/bin/python3
"""Fit the published JLC/EasyEDA pad centres to actual KiCad pads at CPL rotation.

Assembly convention assumption: 0° is the library drawing seen from the
assembly side, with counterclockwise rotation. The assembler preview remains
mandatory. Only centre positions are compared, not land sizes or paste.
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
LIMIT = 0.35  # mm; includes distinct land spacing/origins and connector tabs


def score(lib, ours, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    err = 0.0
    for pad, points in lib.items():
        rotated = [(c*x - s*y, s*x + c*y) for x, y in points]
        err = max(err, min(max(math.dist(a, b) for a, b in zip(rotated, q))
                           for q in permutations(ours[pad])))
    return err


def verify(pcb, bom, cpl):
    libdata = json.loads(LIB.read_text())["parts"]
    with bom.open(newline="") as f:
        parts = {r: row["LCSC Part #"] for row in csv.DictReader(f) for r in row["Designator"].split(",")}
    with cpl.open(newline="") as f:
        rows = list(csv.DictReader(f))
    poses = {row["Designator"]: row for row in rows}
    if len(rows) != len(poses) or set(parts) != set(poses):
        raise ValueError("CPL must contain exactly one placement per BOM reference")
    board = k.LoadBoard(str(pcb))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    worst = 0.0
    errors = []
    for ref, lcsc in sorted(parts.items()):
        row, f = poses[ref], fps[ref]
        back = f.GetLayer() == k.B_Cu
        if row["Layer"] != ("Bottom" if back else "Top"):
            raise ValueError(f"{ref}: incorrect CPL side")
        x, y = (float(row[name].removesuffix("mm")) for name in ("Mid X", "Mid Y"))
        angle = float(row["Rotation"])
        ours, lib = {}, {}
        for pad in f.Pads():
            if pad.GetAttribute() == k.PAD_ATTRIB_SMD:
                q = pad.GetPosition()
                ours.setdefault(pad.GetNumber(), []).append(((k.ToMM(q.x) - x)*(-1 if back else 1), -k.ToMM(q.y) - y))
        for n, px, py in libdata[lcsc]:
            lib.setdefault("MP" if n in MP.get(lcsc, ()) else n, []).append((px, py))
        if {n: len(p) for n, p in ours.items()} != {n: len(p) for n, p in lib.items()}:
            raise ValueError(f"{ref} {lcsc}: library and board pad numbers/counts differ")
        error = score(lib, ours, angle)
        worst = max(worst, error)
        best = min((score(lib, ours, a), a) for a in (0, 90, 180, 270))
        if error > LIMIT:
            errors.append(ref)
        print(f"{ref:4} {lcsc:10} {angle:3g}° {error:.3f} mm; best {best[1]:3g}° {best[0]:.3f} mm")
    print(f"CPL fit: {len(poses)} parts, {len(errors)} failed, max pad-centre error {worst:.3f} mm (limit {LIMIT:.2f} mm)")
    return bool(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    name = ROOT / "fab" / f"{STEM}-rev{REV}"
    parser.add_argument("--pcb", type=Path, default=ROOT / (STEM + ".kicad_pcb"))
    parser.add_argument("--bom", type=Path, default=Path(f"{name}-bom-jlc.csv"))
    parser.add_argument("--cpl", type=Path, default=Path(f"{name}-cpl-jlc.csv"))
    args = parser.parse_args()
    raise SystemExit(verify(args.pcb, args.bom, args.cpl))
