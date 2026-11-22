"""Fail on a partial or stale handoff. Does not turn physical holds into passes."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
base=ROOT/"workbench/public/prototype"
scene=json.loads((base/"scene.json").read_text())
prefix="tapir-rev-a/"
assert scene["validation"]["disposition"]=="HOLD"
assert scene["validation"]["rows"] and scene["geometryChecks"]["passing"]==scene["geometryChecks"]["count"]
with ZipFile(base/"tapir-rev-a.zip") as z:
    assert z.testzip() is None
    crc={}
    for line in z.read(prefix+"SHA256SUMS").decode().splitlines():
        h,name=line.split("  ",1);assert name not in crc and not Path(name).is_absolute() and ".." not in Path(name).parts
        crc[name]=h
    assert len(crc)==len(z.namelist())-1
    assert all(hashlib.sha256(z.read(prefix+p)).hexdigest()==v for p,v in crc.items())
    def inside(rel):return z.read(prefix+rel)
    assert json.loads(inside("product/validation/results.json"))==scene["validation"]
    for p,h in scene["validation"]["inputs_sha256"].items():
        assert crc.get(p)==h, f"Packaged file is absent or differs from independent verification: {p}"
    assert json.loads(inside("product/design/geometry.json"))==scene["geometry"]
    assert json.loads(inside("product/mechanical/build/clearances.json"))==scene["cadEvidence"]
    assert len(scene["cadEvidence"]["halves"])==2
    for hand in ("left","right"):
        pcb=f"product/electronics/{hand}/tapir-{hand}.kicad_pcb"
        assert pcb in crc and crc[pcb]==scene["validation"]["inputs_sha256"][pcb]
        r=json.loads(inside(f"product/electronics/reports/tapir-{hand}-routing.json"))
        assert r["passes"] and r["project_drc_exclusions"]==0 and not any(r["native_counts"].values())
        assert len(scene["native"][hand]["tracks"])==r["trace_segments"]
        assert set(s["ref"] for s in scene["native"][hand]["models"]).issuperset({f"SW{i}" for i in range(1,22)})
        assert f"product/firmware/build-evidence/{hand}/zmk.uf2" in crc
        assert f"product/mechanical/build/{hand}/assembly.step" in crc
        cad=json.loads(inside(f"product/mechanical/build/{hand}/clearances.json"))
        assert cad in scene["cadEvidence"]["halves"] and cad["geometry_sha256"]==crc["product/design/geometry.json"]
        assert not any(r["status"].startswith("FAIL") for r in cad["checks"])
        assert {"pcb_into_tray","bezel_onto_caseless_assembly","usb_straight_insertion"} <= {p["id"] for p in cad["paths"]}
        wire=json.loads(inside(f"product/mechanical/build/{hand}/battery-wire-105mm.json"))
        assert abs(wire["centerlineLength_mm"]-105.0)<0.001
        assert f"product/design/build/{hand}-reach-1to1.svg" in crc
        assert len([p for p in crc if p.startswith(f"product/electronics/build/fabrication/{hand}/") and p.endswith(".gbr")])>=6
        assert any(p.startswith(f"product/electronics/build/fabrication/{hand}/") and p.endswith(".drl") for p in crc)
        parts=[p for p in scene["meshes"] if p["hand"]==hand]
        assert set(p["role"] for p in parts)==({"cover","tray","retainer"}|({"bridge"} if hand=="right" else set()))
        for p in parts:
            assert hashlib.sha256((base/p["stl"]).read_bytes()).hexdigest()==p["sha256"]
            assert crc["product/mechanical/build/"+p["stl"].removeprefix("cad/")]==p["sha256"]
    for f in scene["componentMeshes"].values():assert (base/f).is_file()
    assert all(p in crc for p in ["product/sourcing/bom.csv","product/electronics/pointer-harness.md","product/RELEASE.md"])
print(f"Verified {len(crc)} package member hashes, both native PCB and CAD reports, meshes, Gerbers, drills and firmware. Physical/product release remains HOLD.")
