#!/usr/bin/python3
"""Check courtyard coverage and measure the closest switch/sensor geometry."""
from itertools import combinations
import json
import math

import pcbnew as k

from design import BATTERY, ROOT, STEM


def mm_dist(a, b):
    return k.ToMM(round(math.dist(tuple(a), tuple(b))))


def calculate(board):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    missing, overlaps = [], []
    sides = {k.F_CrtYd: [], k.B_CrtYd: []}
    for ref, f in sorted(fps.items()):
        n = 0
        for layer, entries in sides.items():
            poly = f.GetCourtyard(layer)
            if poly.OutlineCount():
                n += 1
                entries.append((ref, poly, poly.BBox()))
        if not n:
            missing.append(ref)
    for entries in sides.values():
        for (ref1, p1, box1), (ref2, p2, box2) in combinations(entries, 2):
            if box1.Intersects(box2):
                q = k.SHAPE_POLY_SET(p1)
                q.BooleanIntersection(p2)
                if q.Area() > 0:
                    overlaps.append([ref1, ref2, round(q.Area() / 1e12, 6)])
    sensor_clearances = {}
    key_centres = {f"K{i}": fps[f"SW{i}"].GetPosition() for i in range(1, 7)}
    for i in range(1, 7):
        hole = max(fps[f"SW{i}"].Pads(), key=lambda p: p.GetDrillSizeX())
        for p in fps[f"U{i}"].Pads():
            shape = k.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(shape, k.B_Cu, 0, k.FromMM(0.001), k.ERROR_OUTSIDE)
            gap = k.ToMM(round(math.sqrt(shape.SquaredDistance(hole.GetPosition())) - hole.GetDrillSizeX()/2))
            sensor_clearances[f"U{i}.{p.GetNumber()}"] = round(gap, 4)
    closest_mount = min((round(mm_dist(centre, fps[f"H{i}"].GetPosition()), 3), key, f"H{i}")
                        for key, centre in key_centres.items() for i in range(1, 5))
    closest_metal_land = min((round(mm_dist(centre, p.GetPosition()), 3), key, r)
                             for key, centre in key_centres.items() for r in ("J1", "S1")
                             for p in fps[r].Pads() if p.GetNumber() == "MP")
    mux_bypass = {}
    for u, c in (("U7", "C7"), ("U8", "C8")):
        pu = {p.GetNumber(): p.GetPosition() for p in fps[u].Pads()}
        pc = {p.GetNumber(): p.GetPosition() for p in fps[c].Pads()}
        mux_bypass[u] = dict(vcc_pad_centres_mm=round(mm_dist(pu["24"], pc["1"]), 3),
                             gnd_pad_centres_mm=round(mm_dist(pu["12"], pc["2"]), 3))
    widths = {net: min(k.ToMM(t.GetWidth()) for t in board.GetTracks()
                       if t.Type() == k.PCB_TRACE_T and t.GetNetname() == net) for net in BATTERY}
    return dict(courtyards={board.GetLayerName(l): len(v) for l, v in sides.items()},
                missing_courtyards=missing, same_side_courtyard_overlaps_mm2=overlaps,
                sensor_land_to_centrehole_mm=sensor_clearances,
                closest_mount_centres_mm=closest_mount, closest_shell_land_centres_mm=closest_metal_land,
                mux_bypass_pad_centres_mm=mux_bypass, minimum_battery_track_widths_mm=widths)


if __name__ == "__main__":
    report = calculate(k.LoadBoard(str(ROOT / (STEM + ".kicad_pcb"))))
    report["pass"] = (not report["missing_courtyards"] and not report["same_side_courtyard_overlaps_mm2"]
                      and min(report["sensor_land_to_centrehole_mm"].values()) >= 0.30
                      and min(report["minimum_battery_track_widths_mm"].values()) >= 0.40)
    (ROOT / "reports" / "mechanical.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Mechanical and battery checks:", json.dumps(report))
    raise SystemExit(0 if report["pass"] else 1)
