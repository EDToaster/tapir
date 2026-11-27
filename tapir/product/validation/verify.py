#!/usr/bin/env python3
"""Independent, fail-closed Tapir cross-domain acceptance. Python 3.10+, KiCad CLI 10."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache

from native import Board, Blocked, nets_from_xml, uf2_info
import contracts as C

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; P=ROOT/"product"
G=P/"design/geometry.json"; E=P/"electronics"; F=P/"firmware"; M=P/"mechanical"
D=F/"config/boards/shields/tapir"; DTI=D/"tapir.dtsi"; KEY=F/"config/tapir.keymap"
V=HERE/"vendor-v11.json"
PASS="PASS_DIGITAL"; PENDING="PHYSICAL_PENDING"


def relative(p):
    try: return Path(p).relative_to(ROOT).as_posix()
    except ValueError: return str(p)


@lru_cache(maxsize=512)
def sha_version(p,size,mtime):
    out=hashlib.sha256()
    with p.open('rb') as data:
        for block in iter(lambda:data.read(1024*1024),b''):out.update(block)
    return out.hexdigest()

def sha(p):
    s=p.stat();return sha_version(p,s.st_size,s.st_mtime_ns)


def cli(args):
    if not shutil.which(args[0]):
        raise Blocked(f"Executable not installed: {args[0]}")
    return subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=240)


def require(p):
    if not p.is_file():
        raise Blocked("Missing input: "+relative(p))
    return p


class Report:
    def __init__(self):
        self.rows=[]; self.digests={}; self.components=[]; self.keys={}

    def row(self,id,scope,fn,paths):
        evidence=[relative(p) for p in paths]
        try:
            for p in paths:
                require(p)
                self.digests[relative(p)]=sha(p)
            result=fn()
            status,observed=(PASS,result) if isinstance(result,str) else result
        except (Blocked,FileNotFoundError) as ex:
            status,observed="BLOCKED",str(ex)
        except Exception as ex:
            status,observed="FAIL",f"{type(ex).__name__}: {ex}"
        self.rows.append(dict(id=id,scope=scope,status=status,observed=observed,evidence=evidence))
        return status

    def pending(self,id,topic,protocol):
        self.rows.append(dict(id=id,scope="physical",status=PENDING,observed=topic,
                             evidence=["product/validation/BENCH.md#"+protocol]))


def native_rules(path,kind,tmp):
    ver=cli(["kicad-cli","--version"]).stdout.strip()
    if not ver.startswith("10."):
        raise Blocked(f"KiCad 10 required; found {ver}")
    out=tmp/f"{path.stem}-{kind}.json"
    args=["kicad-cli",*(["pcb","drc","--schematic-parity","--all-track-errors"] if kind=="drc" else ["sch","erc"]),
          "--severity-all","--exit-code-violations","--format","json","-o",out,path]
    cp=cli(args)
    if not out.exists():
        raise ValueError(f"KiCad {cp.returncode}: {cp.stderr[-400:] or cp.stdout[-400:]}")
    raw=json.loads(out.read_text())
    result=list(raw.get("violations",[]))+list(raw.get("unconnected_items",[]))+list(raw.get("schematic_parity",[]))
    for sheet in raw.get("sheets",[]):
        result.extend(sheet.get("violations",[]))
    info=Counter(x.get("type","unknown") for x in result)
    summary=f"KiCad {ver}; {len(result)} findings incl warnings and exclusions; "+(", ".join(f"{k}={v}" for k,v in sorted(info.items())) or "none")
    if not (("violations" in raw and "unconnected_items" in raw and "schematic_parity" in raw) if kind=="drc" else "sheets" in raw):
        raise ValueError("Unrecognized native report shape")
    return (PASS if cp.returncode==0 and not result else "FAIL",summary+f"; CLI exit {cp.returncode}")


def get_xml(sch,tmp):
    require(sch)
    file=tmp/(sch.stem+".xml")
    cp=cli(["kicad-cli","sch","export","netlist","--format","kicadxml","-o",file,sch])
    C.demand(cp.returncode==0,cp.stderr[-400:]); return nets_from_xml(file)


def charger():
    q=json.loads(V.read_text()); i=q["iset"]
    r=i["default_to_ground_ohm"]
    hi=i["ki_max_aohm"]/((1-i["assumed_r_tolerance"])*r)*1000
    lo=i["ki_min_aohm"]/((1+i["assumed_r_tolerance"])*r)*1000
    C.demand(q["charger_marked"]=="BQ25100" and hi<100<2*hi,"charger margin unexpected")
    dt=C.read_clean(DTI)
    hog=re.search(r'charge_rate_safe\s*\{([^}]+)\}',dt)
    C.demand(hog and "input;" in hog[1] and re.search(r'gpios\s*=\s*<13\s+GPIO_ACTIVE_HIGH>',hog[1]) and
             not re.search(r'GPIO_PULL|output-|GPIO_OUTPUT',hog[1]),"P0.13 not assigned high-Z in application")
    return (f"Seeed Plus v1.1 schematic marks {q['charger_marked']}, 2.7k ISET to GND + 2.7k to P0.13; high-Z application source. "
            f"Conditional bound {lo:.2f}–{hi:.2f} mA (assumed ±1% R) below 100 mA; actively low could reach {2*hi:.2f} mA. Bootloader/actual module not verified.")


def pointer_pins(ep):
    props={"PS2_DATA":("11","sda-gpios"),"PS2_CLK":("15","scl-gpios"),"PS2_RST":("16","rst-gpios"),"PTR_EN":("17","enable-gpios")}
    vendor=json.loads(V.read_text())["module_pads"]; overlay=C.read_clean(D/"tapir_right.overlay")
    pins=[]
    for net,(pad,prop) in props.items():
        p=re.search(r'P([01])\.(\d+)',vendor[pad])
        d=re.search(prop+r'\s*=\s*<&gpio([01])\s+(\d+)\s+GPIO_ACTIVE_HIGH>',overlay)
        C.demand(ep.get(("U1",pad))==net and p and d and list(map(int,p.groups()))==list(map(int,d.groups())),f"{net}/{pad}: vendor/firmware/board mismatch")
        pins.append(f"{net}=P{p[1]}.{int(p[2]):02d}")
    return "4/4 from board U1 pad through manufacturer v1.1 netlist into pin + polarity in right overlay; "+", ".join(pins)


def add_half(report,hand,tmp,h,bindings):
    stem="tapir-"+hand; base=E/hand; pcb=base/(stem+".kicad_pcb"); sch=base/(stem+".kicad_sch")
    pro=base/(stem+".kicad_pro"); ov=D/(stem.replace("-","_")+".overlay")
    cache={}
    def b():
        if "board" not in cache: cache["board"]=Board(require(pcb))
        return cache["board"]
    def x():
        if "xml" not in cache: cache["xml"]=get_xml(sch,tmp)
        return cache["xml"]
    def add(k,scope,fn,files):
        return report.row(hand+"."+k,scope,fn,files)
    add("erc","electrical",lambda:native_rules(sch,"erc",tmp),[sch,pro])
    add("drc-parity","electrical",lambda:native_rules(pcb,"drc",tmp),[sch,pcb,pro])
    add("schematic-endpoints","electrical",lambda:C.endpoints(x(),hand),[sch])
    add("pcb-endpoints","electrical",lambda:C.endpoints(b().endpoints(),hand),[pcb])
    def parity():
        a=x(); c=b().endpoints()
        dif=[f"{k}:{a.get(k)} != {c.get(k)}" for k in sorted(set(a)|set(c)) if a.get(k)!=c.get(k)]
        C.demand(not dif,"; ".join(dif[:20]))
        C.demand(b().tracks>0,"No routed copper segments")
        return f"{len(c)} native XML ⇔ board endpoints agree; {b().tracks} copper segments/arcs, {b().vias} vias; native DRC separately tests continuity"
    add("endpoint-parity","electrical",parity,[pcb,sch])
    add("carrier-contour","mechanical",lambda:C.outline(b(),h()),[pcb,G])
    add("mount-registration","mechanical",lambda:C.holes(b(),h()),[pcb,G])
    add("all-footprint-drills","mechanical",lambda:C.every_drill(b(),h()),[pcb,G])
    add("switch-registration","mechanical",lambda:C.placement(b(),h()),[pcb,G])
    add("cap-stroke","mechanical",lambda:C.sweep(h()),[G])
    add("cell-envelope","power",lambda:C.battery(h()),[G,V])
    def topology():
        mapping=C.topology(h(),b().endpoints(),C.read_clean(DTI)+C.read_clean(D/"tapir-transform.dtsi"),C.read_clean(ov),hand)
        C.demand(len(mapping)==(24 if hand=="left" else 21),"missing physical key")
        report.keys[hand]=sorted(mapping,key=lambda a:a["logical"])
        return f"{len(mapping)} physical positions traced from placed electrical pad through diode and controller to firmware slots; no aliases"
    add("matrix-to-firmware","integration",topology,[G,pcb,DTI,D/"tapir-transform.dtsi",ov])
    if hand=="right":
        add("pointer-pins","integration",lambda:pointer_pins(b().endpoints()),[pcb,ov,V])
    def inventory():
        parts=b().parts; ex=C.expected(hand); g=h()
        for ref,part in sorted(parts.items()):
            notes=[]
            nets={k[1]:v for k,v in b().endpoints().items() if k[0]==ref}
            if ref.startswith("H"):
                exp=g["mountingHoles"]; match=any(ref==a["ref"] for a in exp)
                notes.append("declared case-mount datum, non-electrical")
            else:
                match=ref in ex and ex[ref]==nets
                notes.append(f"{len(nets)} assigned functional pins compared with independent expected nets")
            report.components.append(dict(hand=hand,ref=ref,value=part["value"],footprint=part["footprint"],side=part["layer"],
                                    net_contract=("NOT_APPLICABLE" if ref.startswith("H") else PASS) if match else "FAIL",physical=PENDING,notes=notes))
        actual=set(parts); want=set(ex)|set(m["ref"] for m in g["mountingHoles"])
        C.demand(actual==want,f"extra {sorted(actual-want)}, absent {sorted(want-actual)}")
        return f"{len(parts)} placed references, independently enumerated incl {len(ex)} electrical parts and {len(want)-len(ex)} mechanical holes"
    add("inventory","sourcing",inventory,[G,pcb])
    return cache


def fw_binary(report,hand,dirs):
    # Explicit package and build-location candidates only; never substitute a different role's UF2.
    alt=dirs.get(hand)
    candidates=([alt/"zephyr/zmk.uf2",alt/"zmk.uf2"] if alt else [])+[F/"build-evidence"/hand/"zmk.uf2"]
    path=next((p for p in candidates if p.is_file()),candidates[0])
    def inspect():
        info=uf2_info(path)
        return f"nRF52840 UF2 {info['blocks']} validated block numbers/family/magic, {info['payload_bytes']} payload bytes, addresses {info['lowest_address']}..{info['end_exclusive']} exclusive; not a flash or HID trial"
    report.row(hand+".uf2","firmware",inspect,[path])
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=HERE/"results.json")
    p.add_argument("--left-build",type=Path); p.add_argument("--right-build",type=Path)
    p.add_argument("--report-only",action="store_true",help="always exit 0 after successfully writing an honest ledger")
    p.add_argument("--release",action="store_true",help="also fail on pending physical gates")
    a=p.parse_args(); report=Report(); geo={}
    def geometry():
        if not geo: geo.update(json.loads(require(G).read_text()))
        return geo
    with tempfile.TemporaryDirectory() as work:
        for hand in ["left","right"]:
            add_half(report,hand,Path(work),lambda h=hand:geometry()["halves"][h],{})
        report.row("keymap.original-42","firmware",lambda:C.layercheck(C.read_clean(KEY)),[KEY])
        report.row("charger.margin","power",charger,[DTI,V])
        builds={"left":a.left_build,"right":a.right_build}
        binaries=[fw_binary(report,h,builds) for h in ["left","right"]]
        def different():
            C.demand(sha(binaries[0])!=sha(binaries[1]),"identical binaries cannot prove distinct hand roles")
            return "Both UF2 digests are different (build configs/roles checked separately)"
        report.row("firmware.distinct","firmware",different,binaries)
        def cover():
            if len(report.keys)!=2: raise Blocked("Both cross-domain matrix traces required")
            all_keys=sum(report.keys.values(),[])
            C.demand(sorted(s["logical"] for s in all_keys)==list(range(45)),"logical positions not bijective")
            return "45/45 global positions reached exactly once; 42 typing positions plus click, scroll, right-click at 42, 43, 44"
        report.row("split.key-coverage","integration",cover,[G,DTI,KEY])
        report.row("power.week-budget","power",lambda:
            f"100 mAh × 80% / 168 h = {100*.8/168:.6f} mA mean per half; 1 h pointer/7 h connected/16 h asleep. Arithmetic target only, not a runtime estimate.",[P/"requirements.md"])
        from followup import enrich
        enrich(report,geometry,builds)
    for k,topic,anchor in [
        ("mounts","M01/M03: actual bores, fastener/tool access, bridge load/retention and removal are unmeasured.","mechanical-and-electrical-inspection"),
        ("stroke","M02/M06: 42 physical switches + caps, 3 buttons, thumb reach and simultaneous presses not exercised.","mechanical-and-electrical-inspection"),
        ("usb","M04: no actual USB overmold, mating stop or closed-case cable measured on either half.","mechanical-and-electrical-inspection"),
        ("pouch","M05: actual maximum pouch/PCM/wires, swelling, insulation and safe closure unverified.","mechanical-and-electrical-inspection"),
        ("polarity","E01/E02: board J1 pin allocation is intent. Exact Adafruit 1570 drawing calls for a reversed plug; verify real pack polarity with meter before connecting, never infer from colors.","mechanical-and-electrical-inspection"),
        ("charge","E02: physical 50 mA mode and peak below 100 mA through reset, DFU, USB hot-plug, suspend and charge termination not measured.","mechanical-and-electrical-inspection"),
        ("power","E03/E04: rail startup and backfeed, both battery-only current integrals, sleep/wake and seven-day runtime not measured.","mechanical-and-electrical-inspection"),
        ("rf","E05: closed-case BLE range/reconnect, hand attenuation and loss under load unmeasured.","mechanical-and-electrical-inspection"),
        ("hid","H01–H04: real host USB/BLE, cross-half drag and scroll, disconnects and recovery not exercised.","host-event-and-fault-matrix")]:
        report.pending("physical."+k,topic,anchor)
    counts=dict(Counter(r["status"] for r in report.rows))
    result=dict(schema=1,disposition="HOLD",counts=counts,rows=report.rows,components=report.components,
                key_trace=report.keys,inputs_sha256=dict(sorted(report.digests.items())),
                interpretation="PASS_DIGITAL is limited to the named test; no physical acceptance or order authorization.")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(f"{relative(a.out)}: HOLD; "+", ".join(f"{n} {s}" for s,n in counts.items()))
    for r in report.rows:
        if r["status"] in ("FAIL","BLOCKED"): print(f"{r['status']}: {r['id']}: {r['observed']}")
    return 0 if a.report_only else int(any(counts.get(s,0) for s in (["FAIL","BLOCKED",PENDING] if a.release else ["FAIL","BLOCKED"])))


if __name__=="__main__":
    sys.exit(main())
