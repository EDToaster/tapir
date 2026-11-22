#!/usr/bin/env python3
"""Package the real design and local evidence. Never submits manufacturing files."""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from reach_sheets import sheet
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"workbench/public/prototype"
CAD=ROOT/"product/mechanical/build"
OUT.mkdir(parents=True,exist_ok=True)
required=ROOT/"product/design/geometry.json"
if not required.is_file():sys.exit("Make product geometry first: node product/design/generate-geometry.mjs")
geo=json.loads(required.read_text())
patterns=ROOT/"product/design/build"
patterns.mkdir(parents=True,exist_ok=True)
for hand,h in geo["halves"].items():
    pat=patterns/(hand+"-reach-1to1.svg");pat.write_text(sheet(h));shutil.copyfile(pat,OUT/pat.name)
meshdata=[]
for folder in ("cad","components"):
    if (OUT/folder).is_dir():shutil.rmtree(OUT/folder)
manifests=[m for h in ("left","right") if (m:=CAD/h/"mesh-manifest.json").exists()]
for manifest in manifests:
    for meta in json.loads(manifest.read_text()):
        assert meta["hand"]==manifest.parent.name
        p=(CAD/meta["stl"]).resolve()
        if not p.is_relative_to(CAD.resolve()) or not p.is_file():raise RuntimeError(meta)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=meta["sha256"]:
            print(f"Skipping unsettled mesh {meta['id']}: regenerate before release.");continue
        dest=OUT/"cad"/p.relative_to(CAD)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        meshdata.append({**meta,"stl":"cad/"+str(p.relative_to(CAD))})
native_path=OUT/"native.json"
# On machines without KiCad the geometry viewer still works. Never substitute
# guessed traces, or leave stale copper from an earlier PCB in the package.
if shutil.which("kicad-cli") and Path("/usr/bin/python3").is_file():
    subprocess.run(["/usr/bin/python3",str(ROOT/"product/release/native_view.py"),str(native_path)],check=True)
else:native_path.write_text("{}\n")
native=json.loads(native_path.read_text())
components={}
for p in (ROOT/"product/electronics/build/webmodels").glob("*.stl"):
    dest=OUT/"components"/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    components[p.stem]="components/"+p.name
def file_json(path,default):return json.loads(path.read_text()) if path.exists() else default
evidence=file_json(ROOT/"product/validation/results.json",{"disposition":"No verified run","rows":[]})
geometry_checks=[r for h in geo["halves"].values() for r in h["checks"]]
info={"meshes":meshdata,"componentMeshes":components,"geometry":geo,"native":native,"validation":evidence,
      "cadEvidence":file_json(CAD/"clearances.json",{"halves":[]}),
      "geometryChecks":{"count":len(geometry_checks),"passing":sum(r.get("status")=="pass" for r in geometry_checks)}}
(OUT/"scene.json").write_text(json.dumps(info,separators=(",",":")))
native_path.unlink(missing_ok=True)
if sys.argv[1:]==["--scene-only"]:
    print(f"Inspection preview only: {len(meshdata)} case meshes, {len(native)} native PCB sides. No new release archive.")
    sys.exit(0)
if sys.argv[1:]:sys.exit("usage: prepare_site.py [--scene-only]")
# Source tree files and regenerated engineering outputs. Keep original paths for
# generators and footprint libraries to resolve; no caches, keys, or toolchains.
from_git=subprocess.check_output(["git","ls-files","-z","--cached","--others","--exclude-standard"],cwd=ROOT).decode().split("\0")
files={}
for relative in from_git:
    if not relative:continue
    if not(relative.startswith(("product/","workbench/","docs/","mechanical/stack/")) or relative in ("AGENTS.md","README.md",".gitattributes",".gitignore")):continue
    p=ROOT/relative
    if p.is_file() and not any(c in {"node_modules","__pycache__","dist"} for c in p.parts):
        files[relative]=p
for p in CAD.rglob("*") if CAD.exists() else []:
    rel=p.relative_to(CAD)
    if not (len(rel.parts)==1 and rel.name in {"clearances.json","viewer-manifest.json"} or
            len(rel.parts)==2 and rel.parts[0] in {"left","right"}):continue
    if p.is_file() and p.suffix.lower() in {".stl",".step",".stp",".json",".svg"}:
        files[str(p.relative_to(ROOT))]=p
# General-purpose tool caches may exist in build directories. Admit only
# deliverable firmware binaries and human-readable physical check artifacts.
for prefix,exts in [("product/firmware/build",{".uf2"})]:
    for p in (ROOT/prefix).rglob("*"):
        if p.is_file() and p.suffix.lower() in exts: files.setdefault(str(p.relative_to(ROOT)),p)
for p in (ROOT/"product/electronics/build/fabrication").rglob("*"):
    if p.is_file() and p.suffix.lower() in {".gbr",".gbrjob",".drl",".rpt",".csv",".md",".json"}:
        files[str(p.relative_to(ROOT))]=p
if not files:raise RuntimeError("Refusing empty product archive")
for p in patterns.glob("*-reach-1to1.svg"):files[str(p.relative_to(ROOT))]=p
hashes=[]
with zipfile.ZipFile(OUT/"tapir-rev-a.zip","w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for name,p in sorted(files.items()):
        payload=p.read_bytes();hashes.append(hashlib.sha256(payload).hexdigest()+"  "+name)
        zi=zipfile.ZipInfo("tapir-rev-a/"+name,(2026,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=(0o755 if p.stat().st_mode&0o111 else 0o644)<<16
        z.writestr(zi,payload)
    z.writestr("tapir-rev-a/SHA256SUMS","\n".join(hashes)+"\n")
print(f"Product site: {len(meshdata)} CAD meshes, {len(native)} native PCB sides, {len(files)} build-package entries; no orders or external submissions.")
