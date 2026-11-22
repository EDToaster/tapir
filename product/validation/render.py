"""Render the recorded native-check ledger without rerunning or changing it."""
import json
from pathlib import Path
from collections import defaultdict

HERE=Path(__file__).resolve().parent
r=json.loads((HERE/"results.json").read_text())
def cell(s): return str(s).replace("|","\\|").replace("\n"," ")
lines=["# Tapir Rev A acceptance ledger","",
       f"Disposition: **{r['disposition']}**. "+", ".join(f"{v} {k}" for k,v in r["counts"].items())+". No physical test was performed or purchase authorized.","",
       "Digital and physical counts cannot be added into a meaningful “percent complete.” Every row is limited to the files, interface and kind of evidence named below. See [the rerun instructions](README.md), [machine-readable ledger and component inventory](results.json), and [manual first-article tests](BENCH.md).","",
       "## Stop conditions",""]
for q in r["rows"]:
    if q["status"] in ("FAIL","BLOCKED"):
        lines.append(f"- **{q['id']} ({q['status']})**: {q['observed']}")
lines+=["","## Evidence by domain",""]
for scope in dict.fromkeys(q["scope"] for q in r["rows"]):
    lines+=[f"### {scope.title()}","","| Check | Disposition | Actual observation |","|---|---|---|"]
    for q in r["rows"]:
        if q["scope"]==scope:
            lines.append(f"| \x60{q['id']}\x60 | {q['status']} | {cell(q['observed'])} |")
    lines.append("")
lines+=["## Physical-key circuit trace","","| Hand | Ref | Legend | XY (mm) | Row/column GPIO | Global matrix | Keymap index |","|---|---|---|---|---|---|---|"]
for h,ks in r["key_trace"].items():
    for k in ks:
        lines.append(f"| {h} | {k['ref']} | {cell(k['label'])} | {k['x']:.2f}, {k['y']:.2f} | {k['row_gpio']}/{k['column_gpio']} | {k['global_matrix'][0]},{k['global_matrix'][1]} | {k['logical']} |")
lines+=["","## Component traveller","","The physical column does not change because CAD models loaded or ERC passed. Grouped non-PCB items show the installed quantity per side; carrier references are one row per placed instance.","",
    "| Hand | Designator / item | Value / identity | Qty | Electrical evidence | BOM line | Model/fit scope and limits | Physical |","|---|---|---|---:|---|---|---|---|"]
for c in r["components"]:
    lines.append(f"| {c['hand']} | {cell(c['ref'])} | {cell(c['value'])} | {c.get('qty',1)} | {c['net_contract']} | {cell(c.get('bom_line','fabricated feature'))} | {cell('; '.join(c.get('fit_scope',['BLOCKED: no fit classification'])))} | {c['physical']} |")
(HERE/"REPORT.md").write_text("\n".join(lines)+"\n")
