#!/usr/bin/python3
"""Write the files a fab and assembler need, after the ERC and DRC gates pass. Uploads and orders nothing.

Outputs in fab/: Gerber + drill zip, JLCPCB-format BOM and placement (CPL) files, and native.json,
which check_cam.py uses to compare the plotted files against the KiCad board.
"""
import csv
import json
import subprocess
import zipfile
from collections import defaultdict
import pcbnew as k
from design import ROOT, STEM, REV, circuit

FAB = ROOT / "fab"
NAME = f"{STEM}-rev{REV}"
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
# Rotation offsets between KiCad footprints and JLCPCB's part library, from the community table at
# github.com/matthewlai/JLCKicadTools (cpl_rotations_db.csv). They cannot be proven offline:
# check every part against the pin-1 marks in JLCPCB's placement preview before paying.
ROTATION = (("SOT-23", -90), ("SSOP-", 270), ("JST_PH_S", 180))


def run(*args):
    subprocess.run(["kicad-cli", *map(str, args)], check=True, stdout=subprocess.DEVNULL)


def main():
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
    archive = FAB / f"{NAME}-gerbers.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(plots.iterdir()):
            info = zipfile.ZipInfo(f.name, date_time=(2026, 11, 27, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())

    board = k.LoadBoard(str(pcb))
    parts = {c["ref"]: c for c in circuit()["components"]}
    fitted = {r: c for r, c in parts.items() if c["fit"] == "jlc" and not c["dnp"]}
    groups = defaultdict(list)
    for ref, c in fitted.items():
        assert c["lcsc"], ref
        groups[(c["value"], c["footprint"].split(":")[1], c["lcsc"], c["mpn"])].append(ref)
    num = lambda r: (r.rstrip("0123456789"), int("".join(ch for ch in r if ch.isdigit())))
    with (FAB / f"{NAME}-bom-jlc.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
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
        c = box.GetCenter(); name = str(fp.GetFPID().GetLibItemName())
        rot = (180 - fp.GetOrientationDegrees()) % 360                 # bottom side: mirror about the Y axis
        rot = (rot + next((d for p, d in ROTATION if name.startswith(p)), 0)) % 360
        rows.append([ref, f"{k.ToMM(c.x):.4f}mm", f"{-k.ToMM(c.y):.4f}mm", "Bottom", f"{rot:g}"])
    assert len(rows) == len(fitted), (len(rows), len(fitted))
    with (FAB / f"{NAME}-cpl-jlc.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(sorted(rows, key=lambda r: num(r[0])))

    truth = {"PTH": [], "NPTH": [], "F_Cu": [], "B_Cu": []}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            x, y = (v / 1e6 for v in p.GetPosition()); d = p.GetDrillSize()
            if d.x:
                assert d.x == d.y, "slot needs manual review"
                truth["NPTH" if p.GetAttribute() == k.PAD_ATTRIB_NPTH else "PTH"].append([x, -y, d.x / 1e6])
            if p.GetNumber():
                for key, layer in (("F_Cu", k.F_Cu), ("B_Cu", k.B_Cu)):
                    if p.IsOnLayer(layer):
                        truth[key].append([fp.GetReference(), p.GetNumber(), x, -y, p.GetNetname()])
    for t in board.GetTracks():
        if t.Type() == k.PCB_VIA_T:
            x, y = (v / 1e6 for v in t.GetPosition()); truth["PTH"].append([x, -y, t.GetDrillValue() / 1e6])
    (ROOT / "build" / "native.json").write_text(json.dumps(truth))
    print(f"{archive.name}: {len(list(plots.iterdir()))} files; BOM {len(groups)} lines / {len(fitted)} parts; CPL {len(rows)} placements")


if __name__ == "__main__":
    main()
