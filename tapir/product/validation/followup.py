"""Cross-check built firmware, shell mesh and purchased/fabricated component records."""
from collections import Counter
import csv
import hashlib
import math
import re
import json
import struct
from pathlib import Path
from functools import lru_cache

from contracts import demand, read_clean, mapcheck, expected
from native import Blocked, Board
from mesh import SectionMesh, cases, pouch, sensor_bores, analog_route
from step_registration import compare as compare_step
from wire import clearance as self_clearance

P=Path(__file__).resolve().parents[1]; E=P/"electronics"; F=P/"firmware"; M=P/"mechanical"
G=P/"design/geometry.json"; D=F/"config/boards/shields/tapir"


def compiled(hand,dts,conf):
    s=dts.read_text(); cfg=conf.read_text()
    opts={k:v for k,v in re.findall(r'^CONFIG_(\w+)=(.+)$',cfg,re.M)}
    for k,v in {"BOARD":'"seeeduino_xiao_ble"',"ZMK_SPLIT":"y","ZMK_SPLIT_BLE":"y",
        "ZMK_SLEEP":"y","ZMK_IDLE_SLEEP_TIMEOUT":"900000","PM_DEVICE":"y","GPIO_HOGS":"y"}.items():
        demand(opts.get(k)==v,f"{k} compiled {opts.get(k)} vs expected {v}")
    demand((opts.get("ZMK_SPLIT_ROLE_CENTRAL")=="y")==(hand=="right"),"compiled split role mismatch")
    if hand=="right":
        demand(opts.get("ZMK_POINTING")=="y" and "gpio-ps2" in s and "zmk,input-mouse-ps2" in s,
               "right PS/2 pointing omitted")
    else: demand("gpio-ps2" not in s,"peripheral unexpectedly controls pointer")
    hog=re.search(r'charge_rate_safe\s*\{([^}]+)\}',s)
    demand(hog and re.search(r'gpios\s*=\s*<\s*0xd\s+0x0\s*>',hog[1]) and "input;" in hog[1],"resolved charge GPIO unsafe")
    scan=re.search(r'kscan0:\s*kscan\s*\{([^}]+)\}',s)[1]
    trans=re.search(r'default_transform:\s*keymap_transform\s*\{([^}]+)\}',s)[1]
    decl=[int(v,0) for v in re.search(r'\bmap\s*=\s*<([^>]+)>',trans)[1].split()]
    exp=mapcheck(read_clean(D/"tapir-transform.dtsi"))
    demand(decl==[r*256+c for r,c in exp],"compiled transform mismatch")
    def gpio_array(prop):
        return [(int(n,0),int(flags,0)) for n,flags in re.findall(r'&xiao_d\s+(\w+)\s+(\w+)',re.search(prop+r'\s*=\s*([^;]+)',scan)[1])]
    demand(gpio_array("row-gpios")==[(n,0x20) for n in range(4)] and
           gpio_array("col-gpios")==[(n,0) for n in (range(4,10) if hand=="left" else reversed(range(4,10)))],
           "compiled GPIO order/flags mismatch")
    demand("wakeup-source;" in scan,"matrix wake source not built")
    return f"Resolved {hand} role, 45 transform cells, 10 row/column GPIOs and wake flags; sleep enabled at 900000 ms and P0.13 compiled as no-pull input; image execution on hardware pending"


def build_paths(hand,alt):
    if alt:
        a=alt/"zephyr"
        if (a/"zephyr.dts").is_file(): return a/"zephyr.dts",a/".config"
    a=F/"build-evidence"/hand
    return a/"zephyr.dts",a/"resolved.config"


def values_and_pose(hand,h,b):
    wanted={**{f"D{i}":"1N4148WS-7-F" for i in range(1,25 if hand=="left" else 22)},
            **{f"SW{i}":"CPG135001D01" for i in range(1,22)},
            "J1":"S2B-PH-SM4-TB(LF)(SN)","S1":"PCM12SMTR","U1":"XIAO nRF52840 Plus"}
    if hand=="left": wanted.update({f"SW{i}":"PTS810SJM250SMTR LFS" for i in [22,23,24]})
    else: wanted.update({"U2":"TPS22918DBVR","R1":"4.7k","R2":"4.7k","R3":"100k","C1":"1uF","C2":"100nF","J2":"SK8707-01-004 host cable"})
    for ref,value in wanted.items():
        demand(b.parts[ref]["value"]==value,f"{ref}: BOM identity/value {b.parts[ref]['value']} != {value}")
    pose={"U1":("xiao",90),"J1":("batteryConnector",0),"S1":("powerSwitch",0)}
    if hand=="right": pose["J2"]=("driverHeader",0)
    dif=[]
    for ref,(key,offs) in pose.items():
        p=b.parts[ref]; q=h["components"][key]
        dif.append(math.dist(p["xy"],[q["x"]+100,q["y"]+100]))
        demand(abs((p["angle"]-(offs-q.get("a",0))+180)%360-180)<0.02,f"{ref} wrong orientation")
    demand(max(dif)<.015,f"connector/module pose mismatch: {dif}")
    return f"{len(wanted)} footprint values matched to expected MPN/value; {len(dif)} XIAO/power/interface orientations and positions registered, worst XY {max(dif):.6f} mm"


def bom_check(report,bom):
    rows=list(csv.DictReader(bom.open()))
    demand(rows and len({r["id"] for r in rows})==len(rows),"BOM empty or duplicate line IDs")
    def refs(text):
        vals=set()
        for prefix,first,_,last in re.findall(r'(?<![\w-])([A-Z]+)(\d+)(?:\.\.([A-Z]+)?(\d+))?(?![\w-])',text):
            vals.update(f"{prefix}{n}" for n in range(int(first),int(last or first)+1))
        return vals
    total=0
    for hand in ["left","right"]:
        b=Board(E/hand/f"tapir-{hand}.kicad_pcb"); need=set(expected(hand))-{"J2"}
        used={}
        for r in rows:
            selected=refs(r[hand+"_refs"])&need
            if not selected: continue
            demand(selected.isdisjoint(used),f"duplicate BOM allocation {hand} {selected & used.keys()}")
            demand(len(selected)==int(r[hand+"_qty"]), f"BOM line {r['id']} {hand}: {len(selected)} placed vs {r[hand+'_qty']} selected")
            for ref in selected: used[ref]=r["id"]
        demand(set(used)==need,f"{hand} missing purchased refs {sorted(need-used.keys())}")
        for c in report.components:
            if c["hand"]==hand and c["ref"] in used: c["bom_line"]=used[c["ref"]]
        total+=len(used)
    scopes={
       "BT":"Maximum-pack envelope, printed pocket and 105 mm nominal lead routing; no actual pouch, heat, strain or polarity validation.",
       "CAP":"Per-switch MBK envelope installed on every switch in carrier STEP and full cap-stroke screen; not an original supplier BRep.",
       "TPK":"Kit parent line, not an extra installed part. See sensor, driver, dome and wire evidence.",
       "TPSEN":"Sensor dimensions, four registered bores and provisional attachment land; actual strain element/adhesive not qualified.",
       "TPDRV":"Detached driver envelope/cover motion and electrical pin contract; actual terminations, retention and solder fillets unmodeled.",
       "TPDOM":"Installed dome and post envelope; force, full deflection, rubber geometry and subjective reach require a physical sample.",
       "WA":"Four analog node assignments documented; lead clearances, strain relief, analog balance, soldering and actual function require assembly.",
       "WD":"Five host pad/node assignments documented; soldering, insulation, strain relief and signal integrity require assembly.",
       "F6":"Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested.",
       "F8":"Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested.",
       "FN":"Native M2 AF4 envelope, pocket, full axial engagement; nut retention/tolerance untested.",
       "PCBA":"Native outline, mounting drill, CAM, seated populated BRep and continuous as-soldered tray sweep.",
       "PCBB":"Native outline, mounting drill, CAM, seated populated BRep and continuous as-soldered tray sweep.",
       "CASETRAY":"Native pan vs emitted STL; bores, board/solder field, floor, wall and service sweeps checked at nominal pose.",
       "CASEBEZ":"Native upper bezel vs emitted STL; cap stroke, release/screwdriver/USB paths and paddle regions checked at nominal pose.",
       "CASECASS":"Seated and descending cassette checked against case and maximum pouch; numerical uncut cable path, no cell was fitted.",
       "BRIDGE":"Native low tabs, feet, controller/USB envelope and lift obstruction; emitted sensor pilot bores; load and attachment untested.",
    }
    for r in rows:
        demand(all(r.get(k,"").strip() for k in ["id","item","mpn","left_qty","right_qty"]),"unidentified BOM row")
    # Off-board lines stay in the component traveller too: no inferred electrical or mechanical fit.
    for r in rows:
        for hand in ["left","right"]:
            if int(r[hand+"_qty"]) and not any(c.get("bom_line")==r["id"] and c["hand"]==hand for c in report.components):
                report.components.append(dict(hand=hand,ref=r[hand+"_refs"] or r["id"],value=r["mpn"],
                    qty=int(r[hand+"_qty"]),bom_line=r["id"],net_contract="NOT_APPLICABLE",physical="PHYSICAL_PENDING",
                    fit_scope=[scopes[r["id"]]],
                    notes=["Procurement/assembly line; quantity/identity only, no measured fit or live stock inferred"]))
    demand(all(c.get("fit_scope") for c in report.components),"unclassified component or model inventory: check STEP registration first")
    return f"{len(rows)} unique BOM lines; {total} purchased on-carrier references mapped to a unique line by side and quantity (excludes bare pads and drilled holes). Off-board items retained separately."


def find_mesh(hand,name):
    base=M/"build"/hand
    poss=sorted(base.rglob(name+".stl"))
    if len(poss)>1:
        poss=[x for x in poss if "print" not in str(x).lower()]
    return poss[0] if len(poss)==1 else base/(name+".stl")


def cam(hand):
    m=E/"build/fabrication"/hand/"manifest.json"; table=json.loads(m.read_text())["sha256"]
    critical={f"{hand}/tapir-{hand}.kicad_pcb",f"{hand}/tapir-{hand}.kicad_sch",f"step/tapir-{hand}-populated.step"}
    demand(critical<=set(table) and len(table)>=20,"CAM manifest omits native board/schematic/STEP")
    for name,hexdigest in table.items():
        p=(E/name).resolve(); demand(p.is_relative_to(E) and hashlib.sha256(p.read_bytes()).hexdigest()==hexdigest,f"CAM hash mismatch: {name}")
    v=json.loads((E/"reports"/f"tapir-{hand}-cam-readback.json").read_text())
    hits=v["drills"]; brd=Board(E/hand/f"tapir-{hand}.kicad_pcb")
    demand(sum(n["hits"] for n in hits.values())==sum(len([p for p in f["pads"] if p["drill"]]) for f in brd.parts.values())+brd.vias,"CAM footprint + via drill count differs from board")
    demand(v["pass"] and len(v["layers"])==9 and all(r["objects"]>0 for r in v["layers"].values()) and
        max(r["max_xyz_or_dia_rounding_mm"] for r in hits.values())<=.001 and v["profile_segments_matched"]==len(brd.outline()),"CAM readback does not reproduce native board")
    return (f"{len(table)} source/output hashes matched; 9 nonempty Gerber layer functions and {hits['PTH']['hits']} PTH + {hits['NPTH']['hits']} NPTH Excellon hits including vias match native board totals; max readback rounding ≤0.001 mm. Not a fabrication order.")


@lru_cache(maxsize=2)
def cad_bundle(hand):
    base=M/"build"/hand
    record=json.loads((base/"clearances.json").read_text())
    demand(record["hand"]==hand and record["geometry_sha256"]==hashlib.sha256(G.read_bytes()).hexdigest(),
           "BRep result is stale or assigned to the other hand")
    data=json.loads((base/"mesh-manifest.json").read_text())
    demand(record.get("mesh_sha256")=={Path(m["stl"]).name:m["sha256"] for m in data},
           "wrong/missing embedded clearance-to-mesh hash binding; regenerate full bundle")
    for m in data:
        demand(hashlib.sha256((base/Path(m["stl"]).name).read_bytes()).hexdigest()==m["sha256"],"emitted STL mismatch: "+m["stl"])
    for key,name in [("assembly_sha256","assembly.step"),("printable_step_sha256","printable-parts.step")]:
        demand(hashlib.sha256((base/name).read_bytes()).hexdigest()==record.get(key),f"stale or missing exact clearance-to-{name} hash")
    demand(record["wire_plan"]["full_three_dimensional_centerline"]==json.loads((base/"battery-wire-105mm.json").read_text()),"wire path and BRep report were not exported together")
    return record


def ocp(hand,k):
    base=M/"build"/hand
    record=cad_bundle(hand)
    checks=record["checks"]; ids={r["id"] for r in checks}
    required={"usb_enclosure","closure_interfaces","cassette_tray","cassette_hood","max_cell_separator",
        "max_cell_enclosure","carrier_in_tray","solder_and_diodes_vs_tray","full_key_motion_vs_plastics",
        "released_switches_vs_cover","insert_as_soldered_board","insert_carrier_over_bosses",
        "lower_bezel_capless_keys","cassette_vertical_onto_cell","JST_withdrawal_vs_all_prints",
        "wire_lane_closed_case","power_switch_access","PCB_screw_tool_access","case_screw_tool_external"}
    common_parts=["bottom-tray","service-bezel","pouch-organizer"]+(["pointer-bridge"] if hand=="right" else [])
    required.update({"actual_populated_KiCad_STEP_vs_all_prints","Qualtek_3021091_01M_named_cable_to_face","nonlocal_wire_self_clearance",
                     "case_M2x8_nut_engagement","PCB_M2x6_nut_engagement"})
    required.update("native_"+n+"_vs_all_plastics" for n in ["xiao","batteryConnector","powerSwitch"])
    required.update("bolt_nut_seating_"+str(i) for i in range(1,8))
    required.update("lower_bezel_over_"+n for n in ["cassette_shelf","cassette_center_form","controller_and_shell","power_actuator","JST_header"])
    required.update("full_105mm_wiring_vs_"+n for n in common_parts+["maximum_pack"])
    if hand=="right":required.update("four_analog_wires_vs_"+n for n in common_parts)
    required|=({"anti_lift_tabs_engage","bridge_native_controller","bridge_usb","bridge_seated_cover","bridge_seated_tray",
                "lower_bezel_over_driver","lower_bezel_over_bridge_deck","lower_bezel_over_bridge_feet","lower_bezel_over_bridge_tabs"}
               if hand=="right" else {"mouse_unpressed_switch_vs_bezel"})
    demand(required==ids and len(ids)==len(checks),f"critical checks missing {required-ids}, not yet classified {ids-required}, or duplicate IDs")
    if k=="engagement":
        nuts=[r for r in checks if r["id"].endswith("_nut_engagement")]
        demand(len(nuts)==2 and all(r["status"]=="PASS_NOMINAL" and r["engagement_mm"]==1.6 and
               r["tipAboveDeskPlane_mm"]>=.79 for r in nuts),"missing full-depth engagement or tip enters desk")
        return "4 × M2×6 + 3 × M2×8; both nominally engage 1.60 mm nuts; tips clear desk by "+"/".join(str(r["tipAboveDeskPlane_mm"]) for r in nuts)+" mm. Physical torque, actual stock and pull-through remain open."
    unknown=[r["id"]+":"+r["status"] for r in checks if r["status"]!="PASS_NOMINAL"]
    wrong=[(r["id"],r[key]) for r in checks for key in ("common_mm3","conservative_common_mm3") if key in r and r[key]>=.00002]
    demand(not (unknown or wrong),f"native CAD rejection or unrecognized status: {unknown}; nonzero material: {wrong}")
    if hand=="right":
        lift=next(r for r in checks if r["id"]=="anti_lift_tabs_engage")
        demand(lift["common_mm3_at_0_50_lift"]>.05,"bridge release negative control did not catch capture")
    manifest=json.loads((base/"mesh-manifest.json").read_text())
    demand({Path(m["stl"]).stem for m in manifest}==set(common_parts),"printed material body missing/added without test scope")
    wire=json.loads((base/"battery-wire-105mm.json").read_text())
    wirelen=sum(math.dist(a,b) for a,b in zip(wire["centerlineXYZ_mm"],wire["centerlineXYZ_mm"][1:]))
    demand(abs(wirelen-105)<.01 and not wire["drawingLimitConfirmed"] and not wire["fittedCableValidated"],"incorrect length or incorrectly marked as fitted")
    for m in manifest:
        file=M/"build"/m["stl"]
        demand(file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==m["sha256"],"exported mesh does not match producer report")
    vols=[r["common_mm3"] for r in checks if "common_mm3" in r]
    wvols=[r["conservative_common_mm3"] for r in checks if "conservative_common_mm3" in r]
    return (f"{len(checks)} required/reported checks; {len(vols)} common-volume screens, worst {max(vols):.7f} mm³ (<0.00002); "
            f"{len(wvols)} swept-wire screens, worst {max(wvols):.6f} mm³; independently summed lead centerline {wirelen:.3f} mm; minimum modeled junction radius {wire['roundJunctionMinRadius_mm']} mm (no vendor limit). "
            f"{len(manifest)} emitted meshes hash-match and current geometry hash. Seating/torque/cable flex not physically tested.")


def hidden():
    d=json.loads((E/"reports/xiao-hidden-lands.json").read_text())
    vendor=json.loads((P/"validation/vendor-v11.json").read_text())
    demand(vendor["sha256"]==d["module_archive_sha256"],"manufacturer revision differs")
    r={x["host_pad"]:x for x in d["pads"]}
    expected={"24":"/SWDIO","25":"/SWDCLK","26":"/RESET","27":"GND_POWER","28":"/VBAT","29":"GND_POWER"}
    demand(set(r)==set(expected),"hidden pad audit incomplete")
    for p,net in expected.items():
        demand(r[p]["module_net"]==net and min(r[p]["bounding_rectangle_overlap_mm"])>0,f"host underside pad {p} does not overlap {net}")
    return ("6/6 hidden host lands registered to Seeed module refs/nets; battery pads have "
            f"{r['28']['bounding_rectangle_overlap_mm'][0]:.4f} × {r['28']['bounding_rectangle_overlap_mm'][1]:.4f} mm nominal bounding-rectangle overlap. No solder paste/reflow/yield proof.")


def populated_step(hand,record,step,details):
    d=cad_bundle(hand)
    r=next(x for x in d["checks"] if x["id"]=="actual_populated_KiCad_STEP_vs_all_prints")
    n,err,bounds,classes=details
    demand(d["hand"]==hand and d["geometry_sha256"]==hashlib.sha256(G.read_bytes()).hexdigest()
      and r["model"]==step.name and r["model_sha256"]==hashlib.sha256(step.read_bytes()).hexdigest(),
      "populated mechanical check stale, different pose or wrong board")
    demand(r["material_instances"]==n and abs(r["applied_Z_mm"]+1.595)<.0001,"some native parts not tested, or wrong pose")
    demand(r["status"]=="PASS_NOMINAL" and r["collisions"]==[],f"native material intersections: {r['collisions']}")
    return (f"All {n} native STEP occurrences (carrier + {n-1} modeled parts/caps), frame −1.595 mm, tested vs all printed bodies by the CAD kernel: no common-volume finding >0.00002 mm³. "
            "Independent AP214 membership/side/placement audit and STL section sweeps are separate. Solder fillets, cable flexibility, terminals and unmodeled internals are not tested by this BRep screen.")


def outer_envelope(hand,h,native_bounds):
    # Native plastic meshes determine the external XYZ limits. Verify nominal
    # assembled PCB parts/knob and cap/screw extents; never include insertion
    # gauges or swept assembly plumbing in the size of the carried product.
    base=M/"build"/hand
    mc=cad_bundle(hand)
    # Printed BRep bounds use native CAD coordinates.
    bounds=mc["enclosure_bounds"][:]
    points=[]
    names=["bottom-tray","service-bezel","pouch-organizer"]+(["pointer-bridge"] if hand=="right" else [])
    for name in names:
        for *v,_ in struct.iter_unpack("<12fH",(base/(name+".stl")).read_bytes()[84:]):
            points.extend(tuple(v[i:i+3]) for i in (3,6,9))
    mb=[min(p[i] for p in points) for i in range(3)]+[max(p[i] for p in points) for i in range(3)]
    demand(max(abs(v-w) for v,w in zip(bounds,mb))<.04,"STEP vs emitted STL external dimensions disagree")
    def merge(b):
        for k in range(3):
            bounds[k]=min(bounds[k],b[k]);bounds[k+3]=max(bounds[k+3],b[k+3])
    merge(native_bounds)
    expected=0
    for s in h["solids"]:
        if s["role"] not in ("keycap","switch","button-paddle","controller","driver","post","stick-cap","sensor",
                             "power-lever","power-switch","battery-connector","usb-shell","battery","switch-tail","matrix-diode"):continue
        xs=[p[0] for p in s["polygon"]];ys=[-p[1] for p in s["polygon"]]
        merge([min(xs),min(ys),s["bottom"],max(xs),max(ys),s["top"]]);expected+=1
    for x,y in mc["mounts_assembled_XY"]:
        merge([x-2.31,-y-2.31,-6,x+2.31,-y+2.31,1.30])
    for x,y in mc["case_screws_assembled_XY"]:
        merge([x-2.31,-y-2.31,-5.5,x+2.31,-y+2.31,3.8])
    native=mc["assembled_physical_bounds"]
    demand(len(native)==6 and max(abs(x-y) for x,y in zip(native,bounds))<.04,
           f"native seated BRep extents disagree with independently composed model: {native} vs {bounds}")
    dims=[bounds[i+3]-bounds[i] for i in range(3)]
    m=h["usbMouth"]; ux,uy=m["direction"]
    plug=[(m["x"]+d*ux-w*uy,-(m["y"]+d*uy+w*ux)) for d in (0,36) for w in (-6.175,6.175)]
    attached=[max(bounds[k+3],max(p[k] for p in plug))-min(bounds[k],min(p[k] for p in plug)) for k in (0,1)]
    knob=(f"Right rubber stick-cap envelope tops at +{h['components']['rubberCap']['top']:.2f} mm and does not set maximum case height." if hand=="right" else "No stick cap on left.")
    return (f"Modeled portable enclosure union {dims[0]:.3f} × {dims[1]:.3f} × {dims[2]:.3f} mm; "
            f"CAD XYZ min {tuple(round(v,3) for v in bounds[:3])} and max {tuple(round(v,3) for v in bounds[3:])}. "
            f"Includes {len(names)} print meshes checked vs native finished BRep; transformed populated STEP model bounding boxes, {expected} component/key/knob/slide envelopes and 7 head/nut locations. {knob} "
            f"Optional feet not fitted; external cable excluded. Separately, nominal seated 36 mm Qualtek rigid overmold alone gives {attached[0]:.3f} × {attached[1]:.3f} mm XY; flexible cable extension, actual stop and bend are unqualified. Not a physical size.")


def enrich(report,geometry,builds):
    for hand in ("left","right"):
        pcb=E/hand/f"tapir-{hand}.kicad_pcb"
        report.row(hand+".cam-readback","electrical",lambda h=hand:cam(h),
            [E/"build/fabrication"/hand/"manifest.json",E/"reports"/f"tapir-{hand}-cam-readback.json",pcb])
        report.row(hand+".part-variants","integration",lambda h=hand,p=pcb:
            values_and_pose(h,geometry()["halves"][h],Board(p)),[pcb,G])
        dts,conf=build_paths(hand,builds.get(hand))
        report.row(hand+".compiled-role","firmware",lambda h=hand,d=dts,c=conf:compiled(h,d,c),[dts,conf,D/"tapir-transform.dtsi"])
        paths=[find_mesh(hand,n) for n in ["bottom-tray","service-bezel"]]; cache={}
        def mesh_test(k):
            if not cache: cache.update(cases(geometry()["halves"][hand],*[SectionMesh(p) for p in paths]))
            return cache[k]
        for key in ["boss-bore","tray-insertion","usb-bezel","bezel-stroke"]:
            report.row(hand+"."+key,"mechanical",lambda k=key:mesh_test(k),[G]+paths)
        more=paths+[find_mesh(hand,"pouch-organizer")]
        report.row(hand+".pouch-to-case","mechanical",lambda h=hand:pouch(geometry()["halves"][h],{p.stem:SectionMesh(p) for p in more}),[G]+more)
        if hand=="right":
            bridge=find_mesh(hand,"pointer-bridge")
            report.row("right.sensor-bores","mechanical",lambda:sensor_bores(geometry()["halves"]["right"],SectionMesh(bridge)),[G,bridge])
        base=M/"build"/hand
        wire=base/"battery-wire-105mm.json"
        report.row(hand+".lead-self-clearance","mechanical",lambda:self_clearance(wire),[wire])
        step=E/"step"/f"tapir-{hand}-populated.step"; detail=[]
        def placements():
            if not detail: detail.extend(compare_step(pcb,step))
            return detail
        def registration():
            n,xy,bb,classes=placements()
            for c in report.components:
                if c["hand"]==hand and c["ref"] in classes: c["fit_scope"]=classes[c["ref"]]
            return (f"Independent AP214 parsing: native board plus {n-1} footprint model occurrences; every reference/model/count, signed side, yaw, Z and XY match the native board (max XY {xy:.8f} mm). "
                    "Each library STEP hash checked against the declared model fidelity; fabricated bores and bare harness pads are intentionally not separate STEP parts.")
        rows=sorted((E/"models").glob("*.step"))
        report.row(hand+".step-placements","integration",registration,[pcb,step,E/"models/manifest.json"]+rows)
        for key in ("brep-motion","engagement"):
            report.row(hand+"."+key,"mechanical",lambda h=hand,k=key:ocp(h,k),
                [G,base/"clearances.json",base/"mesh-manifest.json",base/"assembly.step",base/"printable-parts.step",base/"battery-wire-105mm.json"])
        all_meshes=more+([bridge] if hand=="right" else [])
        if hand=="right":
            report.row("right.analog-harness-prints","mechanical",lambda:analog_route(geometry()["halves"]["right"],
                {f.stem:SectionMesh(f) for f in all_meshes}),[G]+all_meshes)
        report.row(hand+".carried-envelope","mechanical",lambda h=hand:outer_envelope(h,geometry()["halves"][h],placements()[2]),
                [G,base/"clearances.json",base/"mesh-manifest.json",step,E/"models/manifest.json"]+all_meshes)
        report.row(hand+".populated-step-fit","integration",lambda h=hand:populated_step(h,base/"clearances.json",step,placements()),
            [pcb,step,G,base/"clearances.json",base/"mesh-manifest.json"]+all_meshes)
    bom=P/"sourcing/bom.csv"
    report.row("bom.placement-accounting","sourcing",lambda:bom_check(report,bom),
               [bom]+[E/h/f"tapir-{h}.kicad_pcb" for h in ("left","right")])
    report.row("charger.voltage-compatibility","power",lambda:("BLOCKED",
      "BQ25100 regulation can reach 4.23 V; pack specifies 4.20 V CC/CV, with no approved +30 mV charging window. A PCM overvoltage trip is NOT a permitted CV limit. Obtain written pack compatibility for the full tolerance or redesign the charger; USB-only testing with both cells disconnected. One good measured unit is not qualification."),
      [P/"validation/vendor-v11.json",P/"validation/BENCH.md"])
    report.row("controller.hidden-lands","integration",hidden,[E/"reports/xiao-hidden-lands.json",P/"validation/vendor-v11.json"])
    def power_floor():
        s=read_clean(D/"tapir_right.overlay")
        demand("disable-clicking;" in s,"explicit pointer click disable missing")
        # No claim that host-side click suppression disables the driver's high-current Z-Tap mode.
        limit=100*.80/7; a=2.09
        off=a+7*.65; on=a+7*1.44
        return (f"Lower-bound budget, not prediction: right driver alone draws {off:.2f} or {on:.2f} mAh/day for 1 h active + 7 h idle, assuming perfect gating 16 h. "
                f"At Z-Tap-disabled typical idle that leaves {(limit-off)/24:.3f} mA mean for both MCU/radio and all other right-half loads. Z-Tap-enabled idle alone would exceed the {limit:.2f} mAh/day target. Host event suppression is not a measured sensor mode.")
    report.row("power.pointer-headroom","power",power_floor,[D/"tapir_right.overlay",P/"requirements.md"])
    trace=F/"build-evidence/native-pointer-events.txt"; snap=F/"tests/pointer/keycode_events.snapshot"
    def event_check():
        actual=trace.read_text().splitlines()
        exp=["move 12/0","buttons 0x01","move 0/-12","buttons 0x00","move 12/0","wheel 2/0",
            "wheel 0/-3","move 0/-24","buttons 0x02","move 12/0","buttons 0x00","move 12/0"]
        demand(actual==exp==snap.read_text().splitlines(),"native HID event order/state mismatch")
        return "12 observed ZMK native events match independent sequence: motion, left held during drag, release, wheel on both axes, return to cursor, right held then release. This did not exercise real PS/2, split BLE, USB or hardware wake."
    report.row("firmware.pointer-events","firmware",event_check,[trace,snap,F/"tests/pointer/native_posix_64.keymap",D/"tapir-listener.dtsi"])
    host=F/"build-evidence/split-ble-host.txt"
    def split_hid():
        log=host.read_text()
        demand("Pairing complete" in log and "[MOUSE SUBSCRIBED]" in log and log.count("notify_func: payload")==13,
               "modeled host did not pair, subscribe and receive exactly 13 notifications")
        pack=[bytes.fromhex(p) for p in re.findall(r'd_02: @[0-9:.]+\s+((?:[a-fA-F0-9]{2}\s+){9})\|',log)]
        d=[struct.unpack("<Bhhhh",p) for p in pack]
        demand(len(d)==13,"bad HOG payload count")
        demand([p[0] for p in d]==[0,1,1,1,1,0,0,0,0,0,2,2,0],"button lifecycle or drag state incorrect")
        demand([(p[1],p[2]) for p in d]==[(12,0),(0,0),(0,-12),(12,0),(12,0),(0,0),(12,0),(0,0),(0,0),(0,-24),(0,0),(12,0),(0,0)],
               "motion leaked while scrolling/incorrect drag deltas")
        demand([p[3:] for p in d]==[(0,0)]*7+[(-3,0),(0,2)]+[(0,0)]*4,"vertical/horizontal wheel or release mismatch")
        return "Independent byte-level decode of 13 × 9-byte mouse reports on paired, subscribed third simulated host: opposing-hand left/right drag and releases, two isolated wheel axes, cursor restored; real RF, plug, PS/2 transducer and abrupt disconnect are untested."
    report.row("firmware.split-ble-hog","firmware",split_hid,[host,F/"tests/split-ble/run.sh",F/"tests/split-ble/peripheral.overlay"])
    checksums=F/"build-evidence/SHA256SUMS"
    def firmware_freeze():
        table={}
        for line in checksums.read_text().splitlines():
            sha,name=line.split(None,1); name=name.strip(); demand(name not in table,f"duplicate firmware checksum {name}")
            table[name]=sha
        want={"split-ble-host.txt","split-ble-decoded.txt","native-pointer-events.txt","dependencies.tsv",
              "../vendor/ps2-driver-5ff0b248.tar.gz"}
        want|={h+"/"+n for h in ("left","right") for n in ("zmk.uf2","zephyr.dts","resolved.config")}
        demand(want<=table.keys(),"missing flashed, resolved or simulated artifacts in firmware checksum list")
        for path,sha in table.items():
            actual=(checksums.parent/path).resolve(); demand(actual.is_relative_to(F) and hashlib.sha256(actual.read_bytes()).hexdigest()==sha,
                f"firmware evidence mismatch: {path}")
        return (f"{len(table)} listed build/test/vendor evidence digests verified, including both handed UF2s, resolved DTS/Kconfigs and actual simulation traces. "
                "The build procedure and clean replay record are supplied; digest checks alone do not certify physical execution.")
    report.row("firmware.evidence-freeze","firmware",firmware_freeze,[checksums,F/"build-evidence/validation.md",F/"tools/build.sh"])
