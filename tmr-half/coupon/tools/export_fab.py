#!/usr/bin/python3
"""Write the files a fab and assembler need, after the ERC and DRC gates pass. Uploads and orders nothing.

Outputs in fab/: Gerber + drill zip, JLCPCB-format BOM and placement (CPL) files, and native.json,
which check_cam.py uses to compare the plotted files against the KiCad board.
"""
import csv
import json
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
import pcbnew as k
from design import ROOT, STEM, REV, circuit

FAB = ROOT / "fab"
NAME = f"{STEM}-rev{REV}"
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
# Rotation offsets for the exact JLCPCB part numbers, verified against the assembly library
# by check_cpl.py. A different package/library part must be checked even if its footprint name matches.
ROTATION = {"C15127": 180, "C55130211": 180, "C98457": 270,
            "C295747": 0, "C221841": 0, "C2286": 180}


def run(*args):
    subprocess.run(["kicad-cli", *map(str, args)], check=True, stdout=subprocess.DEVNULL)


def make_gerbers():
    sch, pcb = ROOT / (STEM + ".kicad_sch"), ROOT / (STEM + ".kicad_pcb")
    assert subprocess.check_output(["kicad-cli", "version"], text=True).strip() == "10.0.8"
    reports = ROOT / "reports"; reports.mkdir(exist_ok=True)
    run("sch", "erc", "--severity-all", "--exit-code-violations", "-o", reports / "erc.rpt", sch)
    run("pcb", "drc", "--schematic-parity", "--all-track-errors", "--severity-all", "--exit-code-violations",
        "--format", "json", "-o", reports / "drc.json", pcb)
    plots = FAB / "gerbers"
    if plots.exists():
        for f in plots.iterdir():
            f.unlink()
    plots.mkdir(parents=True, exist_ok=True)
    run("pcb", "export", "gerbers", "--precision", "6", "--layers", LAYERS, "--subtract-soldermask", "-o", plots, pcb)
    run("pcb", "export", "drill", "--excellon-units", "mm", "--excellon-separate-th", "-o", plots, pcb)
    for f in plots.glob("*.gbrjob"):
        f.unlink()
    # KiCad stamps every plot and drill header with the wall-clock plot time.
    # Strip only creation metadata; preserve the coordinate data byte for byte.
    for f in plots.iterdir():
        data = f.read_bytes()
        stable = re.sub(rb"^.*(?:TF\.CreationDate|#@! TF\.CreationDate).*\r?\n", b"", data, flags=re.M)
        stable = re.sub(rb"(?m)^(G04 Created by KiCad \(PCBNEW [^)]+\)) date [^*\r\n]*\*", rb"\1*", stable)
        stable = re.sub(rb"(?m)^(; DRILL file .*?) date [^\r\n]*", rb"\1", stable)
        f.write_bytes(stable)
    archive = FAB / f"{NAME}-gerbers.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(plots.iterdir()):
            info = zipfile.ZipInfo(f.name, date_time=(2026, 11, 27, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    print(f"{archive.name}: {len(list(plots.iterdir()))} files")


def make_placement(board):
    parts = {c["ref"]: c for c in circuit()["components"]}
    fitted = {r: c for r, c in parts.items() if c["fit"] == "jlc" and not c["dnp"]}
    groups = defaultdict(list)
    for ref, c in fitted.items():
        assert c["lcsc"], ref
        groups[(c["value"], c["footprint"].split(":")[1], c["lcsc"], c["mpn"])].append(ref)
    num = lambda r: (r.rstrip("0123456789"), int("".join(ch for ch in r if ch.isdigit())))
    with (FAB / f"{NAME}-bom-jlc.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc, mpn), refs in sorted(groups.items(), key=lambda g: num(sorted(g[1], key=num)[0])):
            w.writerow([mpn or value, ",".join(sorted(refs, key=num)), fp, lcsc])
    rows = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in fitted:
            continue
        assert fp.GetLayer() == k.B_Cu, f"{ref}: every assembled part is expected on the bottom"
        box = None
        for pad in fp.Pads():
            if pad.GetAttribute() == k.PAD_ATTRIB_SMD:
                b = pad.GetBoundingBox()
                if box is None:
                    box = b
                else:
                    box.Merge(b)
        c = box.GetCenter()
        rot = (180 - fp.GetOrientationDegrees()) % 360                 # bottom side: mirror about the Y axis
        rot = (rot + ROTATION.get(fitted[ref]["lcsc"], 0)) % 360
        rows.append([ref, f"{k.ToMM(c.x):.4f}mm", f"{-k.ToMM(c.y):.4f}mm", "Bottom", f"{rot:g}"])
    assert len(rows) == len(fitted), (len(rows), len(fitted))
    with (FAB / f"{NAME}-cpl-jlc.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(sorted(rows, key=lambda r: num(r[0])))
    print(f"BOM {len(groups)} lines / {len(fitted)} parts; CPL {len(rows)} placements")


def native(board):
    truth = {"PTH": [], "NPTH": [], "F_Cu": [], "B_Cu": [], "vias": [], "switches": {},
             "silk_text": {"F": [], "B": []}}
    layer_ids = {k.F_SilkS: "F", k.B_SilkS: "B"}

    def text(item):
        if (item.GetClass() in ("PCB_TEXT", "FP_TEXT", "PCB_FIELD") and item.GetLayer() in layer_ids
                and (not hasattr(item, "IsVisible") or item.IsVisible())):
            truth["silk_text"][layer_ids[item.GetLayer()]].append(
                [item.GetText(), k.ToMM(item.GetTextHeight()), k.ToMM(item.GetTextThickness())])

    for item in board.GetDrawings():
        text(item)
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("SW"):
            x, y = (k.ToMM(v) for v in fp.GetPosition())
            truth["switches"][fp.GetReference()] = [x, -y]
        text(fp.Reference())
        text(fp.Value())
        for item in fp.GraphicalItems():
            text(item)
        for p in fp.Pads():
            x, y = (v / 1e6 for v in p.GetPosition()); d = p.GetDrillSize()
            if d.x:
                assert d.x == d.y, "slot needs manual review"
                truth["NPTH" if p.GetAttribute() == k.PAD_ATTRIB_NPTH else "PTH"].append([x, -y, d.x / 1e6])
            if p.GetNumber() or fp.GetReference().startswith("FID"):
                for key, layer in (("F_Cu", k.F_Cu), ("B_Cu", k.B_Cu)):
                    if p.IsOnLayer(layer):
                        truth[key].append([fp.GetReference(), p.GetNumber(), x, -y, p.GetNetname()])
    for t in board.GetTracks():
        if t.Type() == k.PCB_VIA_T:
            x, y = (v / 1e6 for v in t.GetPosition()); truth["PTH"].append([x, -y, t.GetDrillValue() / 1e6])
            truth["vias"].append(truth["PTH"][-1])
    (ROOT / "build" / "native.json").write_text(json.dumps(truth))


if __name__ == "__main__":
    if sys.argv[1:] == ["--placed"]:
        # For developing and testing the rotation gate without routing or a fabrication export.
        make_placement(k.LoadBoard(str(ROOT / "build" / (STEM + ".kicad_pcb"))))
    else:
        make_gerbers()
        board = k.LoadBoard(str(ROOT / (STEM + ".kicad_pcb")))
        make_placement(board)
        native(board)
