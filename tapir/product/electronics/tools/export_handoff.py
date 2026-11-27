#!/usr/bin/env python3
"""Export local engineering-review files ONLY after native ERC / DRC pass.

No supplier API, email or order is invoked. Review every fabrication drawing,
set explicit layer options with the chosen manufacturer, and get human approval
before supplying any manufacturing data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from design import ROOT

def run(*args):
    subprocess.run(["kicad-cli", *map(str,args)],check=True)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def export(h,cam_python):
    stem="tapir-"+h
    sch=ROOT/h/(stem+".kicad_sch");pcb=sch.with_suffix(".kicad_pcb")
    if subprocess.check_output(["kicad-cli","version"],text=True).strip()!="10.0.8":
        raise RuntimeError("Preview rebuild is pinned to KiCad 10.0.8")
    gate=json.loads((ROOT/"reports"/f"{stem}-routing.json").read_text())
    if (not gate["passes"] or gate.get("board_sha256")!=digest(pcb)
            or any(gate["native_counts"].values()) or set(gate.get("ground_zones",[]))!={"GND return F.Cu","GND return B.Cu"}):
        raise RuntimeError("Board differs from verified final two-plane routed source; rerun the routing gates.")
    dest=ROOT/"build"/"fabrication"/h
    plots=dest/"layers-and-drills";plots.mkdir(exist_ok=True,parents=True)
    step=ROOT/"step"/(stem+"-populated.step");step.parent.mkdir(exist_ok=True)
    run("sch","erc","--severity-all","--exit-code-violations","-o",dest/"erc.rpt",sch)
    run("pcb","drc","--schematic-parity","--all-track-errors","--severity-all",
        "--exit-code-violations","-o",dest/"drc.rpt",pcb)
    run("pcb","export","gerbers","--precision","6","--no-protel-ext","--layers",
        "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts",
        "--subtract-soldermask","-o",plots,pcb)
    run("pcb","export","drill","--excellon-units","mm","--excellon-separate-th",
        "--generate-report","--report-path",dest/"drill-hits.rpt","-o",plots,pcb)
    run("pcb","export","pos","--format","csv","--units","mm","--side","both","--exclude-dnp","-o",dest/"placements-mm.csv",pcb)
    run("sch","export","bom","--fields","Reference,Value,Footprint,QUANTITY","--labels","References,Value,Footprint,Quantity",
        "--group-by","Value,Footprint","--exclude-dnp","-o",dest/"board-bom.csv",sch)
    run("pcb","export","step","--user-origin","100x100mm","--subst-models","--no-dnp","--force","-o",step,pcb)
    subprocess.run([cam_python, str(ROOT/"tools"/"check_cam.py"),h,"--dir",str(dest),"--save-to",str(dest/"cam-readback.json")], check=True)
    (dest/"README.md").write_text(f"""# ENGINEERING PREVIEW / NOT RELEASED

Tapir Rev A: {h} hand only. Do not place an order from this folder.
Production inputs are the editable native KiCad source and the separate full
product BOM. This preview includes board-only BOM + position data, NOT a turnkey
PCBA order or priced purchasing list. J2, where present, is a five-wire hand
termination, not a pick-and-place connector; switch bodies are direct-soldered.

Compare the source SHA-256 in manifest.json. Inspect both copper layers, both
masks, both silkscreens, both paste stencils, the single closed Edge.Cuts
outline and both separate drill files in an independent viewer. Verify drill
types/sizes, holes/edge clearance, Choc and module orientation, JST polarity,
position origins and bottom rotation with the intended assembler. Review paste
on XIAO underside contacts and the selected switch geometry against real parts.
Two copper layers, FR-4 1.6 mm nominal, 1 oz outer copper, ENIG, tented vias.
These are requested process options: in particular a KiCad job Finish of
"None" means unspecified, NOT permission to ship bare copper. Set ENIG
explicitly and confirm the signed stackup and mask process with the fabricator.
cam-readback.json compares the layers, copper lands, profile and every
drill hit against native geometry; it is not an approval or electrical test.
No electronic quote, order or upload was requested or performed.
""")
    files=sorted([f for f in dest.rglob("*") if f.is_file() and f.name!="manifest.json"]+[step,sch,pcb,pcb.with_suffix(".kicad_pro")])
    (dest/"manifest.json").write_text(json.dumps({"status":"engineering-review only; not released for purchase or manufacture",
        "kicad":subprocess.check_output(["kicad-cli","version"],text=True).strip(),
        "sha256":{str(f.relative_to(ROOT)):digest(f) for f in files}},indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("hand",choices=("left","right"))
    p.add_argument("--cam-python",default=os.environ.get("TAPIR_CAM_PYTHON","python3"),help="Python environment with gerbonara==1.6.3")
    args=p.parse_args();export(args.hand,args.cam_python)
