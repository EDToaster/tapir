"""Render the checked JSON evidence into a readable prototype approval record."""
import collections
import json
from pathlib import Path

PRODUCT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((PRODUCT/path).read_text())
def clean(v):return str(v).replace("|","/").replace("\n"," ").strip()
v=read("validation/results.json")
rows=v["rows"]
totals=collections.Counter(r["status"] for r in rows)
assert dict(totals)==v["counts"]
g=read("design/geometry.json")
cpath=PRODUCT/"mechanical/build/clearances.json"
c=json.loads(cpath.read_text()) if cpath.exists() else {"halves":[]}
text=[
    "# Rev A prototype decision",
    "",
    "Disposition: **"+v["disposition"]+"**. No fabrication, purchase or real-cell charging authorization. Digital results apply only to the named input files. No physical first article has been built or tested.",
    "",
    "## Scope and evidence",
    "",
    " · ".join(f"{n} {s.replace('_',' ').lower()}" for s,n in totals.items())+". See the [per-check and per-component report](validation/REPORT.md), [machine-readable results with input hashes](validation/results.json) and [bench acceptance card](validation/BENCH.md).",
    "",
    "| Hand | Carrier envelope (mm) | Modeled assembled envelope excluding cable (mm) | Native copper |",
    "| --- | ---: | ---: | --- |",
]
for hand in ("left","right"):
    geo=g["halves"][hand]["bounds"]
    r=read(f"electronics/reports/tapir-{hand}-routing.json")
    q=next((p for p in c["halves"] if p["hand"]==hand),{})
    bounds=q.get("assembled_physical_bounds",[])
    case="Not available"
    if len(bounds)==6:
        # kernel.bounds uses xmin,ymin,zmin,xmax,ymax,zmax
        case=" × ".join(f"{bounds[i+3]-bounds[i]:.2f}" for i in range(3))
    text.append(f"| {hand.title()} | {geo['w']:.2f} × {geo['h']:.2f} | {case} | [{r['trace_segments']} segments, {r['through_vias']} vias](electronics/reports/tapir-{hand}-routing.json) |")
text += ["","The assembled bounds include the printed parts, populated boards, keycaps, controls, battery and fasteners, but not a mated cable, optional feet or manufacturing variation. Native motion checks and assembly STEP/STL files are in the build package. A [named Qualtek USB-C cable drawing](https://www.qualtekusa.com/images/Cable%20Assemblies/PDF_2/3021091-01M.pdf) anchors the external plug study; it cannot certify the real latch, insertion stop or electrical contacts.","",
    "## What keeps the build on hold","","| Check | Status | Observation |","| --- | --- | --- |"]
for r in rows:
    if r["status"]!="PASS_DIGITAL":text.append("| "+r["id"]+" | "+r["status"]+" | "+clean(r["observed"])+" |")
text+=["","Review the [part-by-part BOM](sourcing/bom.csv), [sourcing exceptions](sourcing/qualification.md), [pointing harness](electronics/pointer-harness.md), and the [power and functional acceptance plan](validation/BENCH.md). Do not count a datasheet allowance, a shelf listing or a USB simulator run as a physical sample measurement.",""]
(PRODUCT/"RELEASE.md").write_text("\n".join(text))
