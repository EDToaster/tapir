#!/usr/bin/python3
"""Compare the six hidden host lands with the B.Cu copper on Seeed's module.

Input: pinned original Seeed board archive and host footprint archive, not
screenshots or a redrawn pinout. Uses KiCad's native geometry reader.
"""
import argparse
import hashlib
import json
import math
import tempfile
import zipfile
from pathlib import Path

import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
MOD_SHA = "f5e4e0e9c7d1725a89be2677549734f6ad96a8e00a16cb1742e0b3abfa99bdd9"
HOST_SHA = "671cb119639e489091b87a64e070d4aba1f22860ddfdbecc85ff143c0c295e28"
HOST_ID = "XIAO-nRF52840-Plus-SMD"


def member(path, sha, suffix):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise ValueError(f"Not the pinned vendor archive: {path}")
    with zipfile.ZipFile(path) as z:
        key, = [x for x in z.namelist() if x.endswith(suffix)]
        return z.read(key)


def pos(p):
    v=p.GetPosition()
    return k.ToMM(v.x),k.ToMM(v.y)


def bbox(p):
    # Hold the SWIG BOX2I owner while retrieving its scalar values.
    box=p.GetBoundingBox()
    return [k.ToMM(v) for v in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom())]


def run(module,host):
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp)
        board=t/"module.kicad_pcb"
        board.write_bytes(member(module,MOD_SHA,"v1.1.kicad_pcb"))
        (t/(HOST_ID+".kicad_mod")).write_bytes(member(host,HOST_SHA,HOST_ID+".kicad_mod"))
        b=k.LoadBoard(str(board))
        orig=k.FootprintLoad(str(t),HOST_ID)
        placed=k.FootprintLoad(str(ROOT/"Tapir.pretty"),HOST_ID)
        footprints={f.GetReference():f for f in b.GetFootprints()}
        originals={p.GetNumber():p for p in orig.Pads()}
        lands={p.GetNumber():p for p in placed.Pads()}
        # Determine origin from opposite castellations, not from any of the six
        # lands under test. Module, host and carrier are all viewed from above.
        # X is estimated on the 4/11 column; Y is midway between the edge pads
        # of the opposite numbered rows. This does not flip the B.Cu test pads.
        cast=list(footprints["U4"].Pads())
        x_basis=[pos(p)[0] for p in cast if p.GetNumber() in ("4","11")]
        y_basis=[pos(p)[1] for p in cast if p.GetNumber() in ("1","14")]
        dx=sum(x_basis)/len(x_basis); dy=(min(y_basis)+max(y_basis))/2
        records=[]
        expected=[("24","TP5","/SWDIO"),("25","TP3","/SWDCLK"),
                  ("26","TP2","/RESET"),("27","TP1","GND_POWER"),
                  ("28","BAT0","/VBAT"),("29","GND0","GND_POWER")]
        q={ref:list(footprints[ref].Pads())[0] for _,ref,_ in expected}
        for num,ref,net in expected:
            hp,op=lands[num],originals[num]
            if pos(hp)!=pos(op) or bbox(hp)!=bbox(op):
                raise ValueError(f"Carrier land {num} has drifted from the source host pattern")
            cp=q[ref]
            if footprints[ref].GetLayer()!=k.B_Cu or cp.GetNetname()!=net:
                raise ValueError(f"{ref} layer or electrical net differs from expected")
            cx,cy=pos(cp); hx,hy=pos(hp); hx+=dx; hy+=dy
            nearest=min(q,key=lambda r: math.dist((hx,hy),pos(q[r])))
            a=bbox(hp); tbox=[a[0]+dx,a[1]+dy,a[2]+dx,a[3]+dy]
            m=bbox(cp)
            overlap=[min(tbox[2],m[2])-max(tbox[0],m[0]),
                     min(tbox[3],m[3])-max(tbox[1],m[1])]
            # Digital screen only. The dimensions below are deliberately not
            # a claim about wettable area, contact resistance or joint yield.
            if nearest!=ref or min(overlap)<.9:
                raise ValueError(f"{num}: nearest={nearest}, bounding overlap={overlap}")
            records.append(dict(host_pad=num,module_ref=ref,module_net=net,
                                host_minus_module_center_mm=[round(hx-cx,4),round(hy-cy,4)],
                                bounding_rectangle_overlap_mm=[round(v,4) for v in overlap]))
        return dict(kicad=k.Version(),module_archive_sha256=MOD_SHA,host_archive_sha256=HOST_SHA,
            module_archive="https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip",
            host_archive="https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip",
            registration="No mirror or rotation; module X from castellation 4/11; Y from row extremes 1/14.",
            host_origin_in_module_board_mm=[round(dx,5),round(dy,5)],
            limit="Nominal CAD bounding-rectangle overlap, not a physical joint or tolerance qualification.",
            pads=records)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("module_archive",type=Path)
    p.add_argument("host_archive",type=Path)
    v=p.parse_args()
    result=run(v.module_archive,v.host_archive)
    dest=ROOT/"reports"/"xiao-hidden-lands.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["pads"],indent=2))
