#!/usr/bin/python3
"""Native ERC + independent component, UUID, pin-type, NC and pad-net comparison.

Run with KiCad 10's Python (pcbnew). Never treats a missing route or design as
a parity pass. --schematic-only deliberately omits the PCB and labels that fact
in the report. Native PCB DRC, connectivity and router checks are separate.
"""
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(hand, board_override=None, sch_only=False):
    stem = f"tapir-{hand}"
    work, reports = ROOT / "build" / hand, ROOT / "reports"
    reports.mkdir(exist_ok=True)
    sch = ROOT / hand / (stem + ".kicad_sch")
    xmlfile = work / "schematic-netlist.xml"
    ercfile = reports / (stem + "-erc.json")
    version = subprocess.check_output(["kicad-cli","version"],text=True).strip()
    if not version.startswith("10."):
        raise ValueError(f"KiCad 10 required; got {version}")
    cmd = ["kicad-cli","sch","erc","--severity-all","--exit-code-violations","--format","json",
           "-o",str(ercfile),str(sch)]
    status = subprocess.run(cmd).returncode
    if status not in (0,5):
        raise RuntimeError(f"ERC did not complete: {status}")
    erc = json.loads(ercfile.read_text())
    erc_count = sum(len(s["violations"]) for s in erc["sheets"])
    reasons = []
    if erc_count or status:
        reasons.append(f"native ERC status={status}, violations={erc_count}")
    pro = json.loads(sch.with_suffix(".kicad_pro").read_text())
    erc_exclusions = pro.get("erc",{}).get("erc_exclusions",[])
    if erc_exclusions:
        reasons.append(f"ERC exclusions: {erc_exclusions}")
    subprocess.run(["kicad-cli","sch","export","netlist","--format","kicadxml",
                    "-o",str(xmlfile),str(sch)],check=True)
    source = work / "design.json"
    intent = {p["ref"]:p for p in json.loads(source.read_text())["components"]}
    root = ET.parse(xmlfile).getroot()
    parts = {p.get("ref"):p for p in root.findall("./components/comp")}
    if set(intent)!=set(parts):
        reasons.append(f"schematic/component-set mismatch: {sorted(set(intent)^set(parts))}")
    endpoints = {}
    unconnected = set()
    net_names = set()
    for net in root.findall("./nets/net"):
        name = net.attrib["name"]
        nodes = net.findall("node")
        is_nc = name.startswith("unconnected-")
        if is_nc and len(nodes)!=1:
            reasons.append(f"NC net {name} has {len(nodes)} endpoints")
        if not is_nc:
            net_names.add(name)
        for node in nodes:
            key = (node.attrib["ref"],node.attrib["pin"])
            if key in endpoints:
                reasons.append(f"{key}: duplicate native schematic net node")
            endpoints[key] = (name,node.attrib["pintype"])
            if is_nc:
                unconnected.add(key)
    expected_pins = {(ref,pin):v for ref,c in intent.items() for pin,v in c["pins"].items()}
    if set(endpoints)!=set(expected_pins):
        reasons.append(f"schematic/intent pin-set mismatch: {sorted(set(endpoints)^set(expected_pins))}")
    for ref in sorted(set(parts)&set(intent)):
        p,c=parts[ref],intent[ref]
        for field,expected in (("value",c["value"]),("footprint",c["footprint"]),("tstamps",c["uuid"])):
            if p.findtext(field)!=expected:
                reasons.append(f"{ref}: XML {field}={p.findtext(field)!r}, intent={expected!r}")
    for key in sorted(set(endpoints)&set(expected_pins)):
        net,typ = endpoints[key]
        p=expected_pins[key]
        expected=p["net"]
        if expected is None:
            if key not in unconnected or not typ.endswith("+no_connect"):
                reasons.append(f"{key}: no explicit NC, schematic={net!r}/{typ}")
        elif net!=expected:
            reasons.append(f"{key}: schematic net={net!r}, intent={expected!r}")
        if typ.removesuffix("+no_connect")!=p["type"]:
            reasons.append(f"{key}: type={typ!r}, intent={p['type']!r}")
    result = dict(kicad_version=version, native_erc_violations=erc_count,
                  erc_exclusions=len(erc_exclusions),
                  erc_ignored_rule_categories=[v["key"] for v in erc.get("ignored_checks",[])],
                  sheet=sch.relative_to(ROOT).as_posix(), sheet_sha256=digest(sch),
                  manifest_sha256=digest(source), schematic_components=len(parts),
                  named_connected_nets=len(net_names), schematic_terminals=len(endpoints),
                  explicit_no_connects=len(unconnected), board_checked=not sch_only)
    if not sch_only:
        import pcbnew
        path = board_override or sch.with_suffix(".kicad_pcb")
        if not path.is_file():
            raise FileNotFoundError(f"No board for parity: {path}")
        board = pcbnew.LoadBoard(str(path))
        seen_pins=set()
        seen_parts=set()
        board_pads=0
        mechanical=[]
        for f in board.GetFootprints():
            ref=f.GetReference()
            if ref in seen_parts:
                reasons.append(f"duplicate board reference: {ref}")
            seen_parts.add(ref)
            if f.GetAttributes() & pcbnew.FP_BOARD_ONLY:
                mechanical.append(ref)
                # Mechanical holes cannot smuggle in signal nets.
                if ref in parts or any(p.GetNetname() for p in f.Pads()):
                    reasons.append(f"{ref}: board-only item with a schematic part or a connected pad")
                continue
            if ref not in parts:
                reasons.append(f"{ref}: PCB part missing in schematic")
                continue
            x=parts[ref]
            for expected,actual,field in ((x.findtext("value"),f.GetValue(),"value"),
                    (x.findtext("footprint"),f.GetFPIDAsString(),"library ID"),
                    ("/"+x.findtext("tstamps"),f.GetPath().AsString(),"instance path")):
                if actual!=expected:
                    reasons.append(f"{ref}: PCB {field}={actual!r}, schematic={expected!r}")
            for p in f.Pads():
                pin=p.GetNumber()
                if not pin:
                    if p.GetNetname():
                        reasons.append(f"{ref}: unnumbered pad carries net {p.GetNetname()}")
                    continue
                key = (ref,pin)
                seen_pins.add(key)
                board_pads+=1
                if key not in endpoints or endpoints[key][0]!=p.GetNetname():
                    reasons.append(f"{ref}.{pin}: PCB={p.GetNetname()!r}, schematic={endpoints.get(key)!r}")
        for key in sorted(set(endpoints)-seen_pins):
            reasons.append(f"{key}: schematic terminal has no PCB pad")
        for ref in sorted(set(parts)-seen_parts):
            reasons.append(f"{ref}: schematic part missing on PCB")
        try:
            loc=path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            loc=path.name
        result.update(board=loc, board_sha256=digest(path), board_numbered_pads=board_pads,
                      board_only_mechanical=sorted(mechanical))
    result.update(passes=not reasons,findings=reasons)
    mode="schematic" if sch_only else "schematic-parity"
    out=reports / (stem + "-" + mode + ".json")
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(f"{stem}: {len(parts)} parts, {len(endpoints)} terminals, {len(unconnected)} explicit NCs; "
          f"{'board omitted' if sch_only else 'board compared'}; {len(reasons)} findings")
    if reasons:
        print("\n".join(reasons))
    return not reasons


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hands",nargs="*",default=["left","right"])
    group=ap.add_mutually_exclusive_group()
    group.add_argument("--board",type=Path,help="check this board instead of the routed board (one hand only)")
    group.add_argument("--schematic-only",action="store_true")
    args=ap.parse_args()
    if any(h not in ("left","right") for h in args.hands) or (args.board and len(args.hands)!=1):
        ap.error("expected left/right; --board requires one hand")
    return 0 if all([check(h,args.board,args.schematic_only) for h in args.hands]) else 1


if __name__=="__main__":
    raise SystemExit(main())
