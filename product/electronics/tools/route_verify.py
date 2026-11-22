#!/usr/bin/python3
"""Check committed copper against native KiCad DRC, schematic and placement."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

import pcbnew

ROOT = Path(__file__).resolve().parents[1]


def save_json(path, val):
    path.write_text(json.dumps(val, indent=2, sort_keys=True) + "\n")


def pads(board):
    # Preserve instances even when pads share a number (e.g. connector tabs).
    # Manufacturing coordinates are KiCad nanometers. DSN -> SES transports
    # copper, not a license to displace a land or swap its net.
    return sorted((f.GetReference(), t.GetNumber(), t.GetNetname(),
                   tuple(t.GetPosition()), tuple(t.GetSize()),
                   round(t.GetOrientation().AsDegrees(), 6), int(t.GetAttribute()),
                   tuple(t.GetDrillSize()), tuple(t.GetLayerSet().Seq()),
                   int(t.GetShape(pcbnew.F_Cu)), int(t.GetShape(pcbnew.B_Cu)))
                  for f in board.GetFootprints() for t in f.Pads())


def verify(hand, routed=None, emitted=None):
    stem = f"tapir-{hand}"
    routed = routed or ROOT / hand / (stem + ".kicad_pcb")
    placed = ROOT / "build" / hand / (stem + ".kicad_pcb")
    if not routed.with_suffix(".kicad_sch").is_file():
        raise ValueError(f"{stem}: no colocated schematic for parity")
    emitted = emitted or ROOT / "reports"
    emitted.mkdir(parents=True, exist_ok=True)
    drc_path = emitted / f"{stem}-drc.json"
    drc_path.unlink(missing_ok=True)
    drc = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--schematic-parity", "--all-track-errors",
         "--severity-all", "--exit-code-violations", "--format", "json", "-o",
         str(drc_path), str(routed)], check=False)
    if drc.returncode not in (0, 5) or not drc_path.is_file():
        raise RuntimeError(f"{stem}: native DRC did not complete ({drc.returncode})")
    report = json.loads(drc_path.read_text())
    board = pcbnew.LoadBoard(str(routed))
    total_by_layer = Counter()
    widths = Counter()
    via_dimensions = Counter()
    net_lengths = Counter()
    segment_count, via_count = 0, 0
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            via_count += 1
            via_dimensions[(round(pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu)), 3),
                            round(pcbnew.ToMM(item.GetDrillValue()), 3))] += 1
        else:
            segment_count += 1
            length = pcbnew.ToMM(item.GetLength())
            widths[round(pcbnew.ToMM(item.GetWidth()), 3)] += 1
            total_by_layer[board.GetLayerName(item.GetLayer())] += length
            net_lengths[item.GetNetname()] += length
    findings = {key: len(report[key]) for key in
                ("unconnected_items", "schematic_parity", "violations")}
    issues = Counter(f["type"] for key in findings for f in report[key])
    project = json.loads(routed.with_suffix(".kicad_pro").read_text())
    exclusions = project["board"]["design_settings"].get("drc_exclusions", [])
    placement = pads(board)
    pad_match = placement == pads(pcbnew.LoadBoard(str(placed)))
    ok = (drc.returncode == 0 and not any(findings.values()) and not exclusions
          and pad_match and segment_count > 0)
    summary = {
        "board": str(routed.relative_to(ROOT)),
        "board_sha256": hashlib.sha256(routed.read_bytes()).hexdigest(),
        "ground_zones": [z.GetZoneName() for z in board.Zones() if not z.GetIsRuleArea()],
        "native_drc": str(drc_path.relative_to(ROOT)),
        "kicad": report["kicad_version"], "passes": ok,
        "native_counts": findings, "findings_by_type": dict(issues),
        "project_drc_exclusions": len(exclusions), "pads": len(placement),
        "routed_pad_geometry_and_nets_match_placement": pad_match,
        "trace_segments": segment_count, "through_vias": via_count,
        "trace_width_mm_count": widths,
        "via_diameter_drill_mm_count": {
            f"{diameter:g}/{drill:g}": count
            for (diameter, drill), count in via_dimensions.items()},
        "route_length_mm_by_layer": {k: round(v, 2) for k, v in total_by_layer.items()},
        "route_length_mm_by_net": {k: round(v, 2) for k, v in net_lengths.items()},
    }
    save_json(emitted / f"{stem}-routing.json", summary)
    print(f"{stem}: {segment_count} segments, {via_count} vias; {findings};"
          f" pad match={pad_match}; pass={ok}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hand", nargs="*", choices=("left", "right"), default=["left", "right"])
    parsed = ap.parse_args()
    raise SystemExit(0 if all(list(map(verify, parsed.hand))) else 1)
