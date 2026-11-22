"""Extract native KiCad copper/holes into the product coordinate frame. No guessed routing."""
import argparse
import json
from pathlib import Path

import pcbnew as k

ROOT = Path(__file__).resolve().parents[2]
CLI = argparse.ArgumentParser()
CLI.add_argument("output", type=Path)
args=CLI.parse_args()
geom=json.loads((ROOT/"product/design/geometry.json").read_text())
def xy(p):
    return [round(k.ToMM(p.x)-100,5),round(k.ToMM(p.y)-100,5)]
def points(seq):
    return [xy(seq.CPoint(i)) for i in range(seq.PointCount())]
def hand(key):
    path=ROOT/f"product/electronics/{key}/tapir-{key}.kicad_pcb"
    if not path.exists():
        return None
    b=k.LoadBoard(str(path)); footprints={s.GetReference():s for s in b.GetFootprints()}
    errors=[]; angles=[]
    for sw in geom["halves"][key]["switches"]:
        fp=footprints[sw["ref"]]
        x,y=xy(fp.GetPosition())
        errors.append(max(abs(x-sw["x"]),abs(y-sw["y"])))
        angles.append(abs((fp.GetOrientationDegrees()+sw["a"]+180)%360-180))
    if max(errors)>.02 or max(angles)>.01:
        raise ValueError(f"{key}: refused to render misregistered circuit: {max(errors)} mm, {max(angles)} degrees")
    result={"maxSwitchCenterResidual":max(errors),"maxSwitchAngleResidual":max(angles),"tracks":[],"pads":[],"holes":[],"vias":[],"models":[]}
    for seg in b.GetTracks():
        if isinstance(seg,k.PCB_VIA):
            x,y=xy(seg.GetPosition());d=k.ToMM(seg.GetDrillValue());result["holes"].append({"x":x,"y":y,"diameter":d})
            result["vias"].append({"x":x,"y":y,"diameter":k.ToMM(seg.GetWidth(k.F_Cu)),"drill":d})
            continue
        side={k.F_Cu:"front",k.B_Cu:"back"}.get(seg.GetLayer())
        if not side: continue
        x1,y1=xy(seg.GetStart());x2,y2=xy(seg.GetEnd())
        result["tracks"].append(dict(x1=x1,y1=y1,x2=x2,y2=y2,width=k.ToMM(seg.GetWidth()),side=side))
    for fp in footprints.values():
        for model in fp.Models():
            # The portable Tapir library binds only identity local placements.
            # Do not silently transpose arbitrary third-party model transforms.
            if any(abs(getattr(v,c)-want)>1e-8 for v,want in
                    [(model.m_Rotation,0),(model.m_Offset,0),(model.m_Scale,1)] for c in "xyz"):
                continue
            if fp.GetLayer()!=k.F_Cu: continue  # bottom packages stay as labeled envelopes
            x,y=xy(fp.GetPosition())
            result["models"].append(dict(ref=fp.GetReference(),model=Path(model.m_Filename).stem,x=x,y=y,a=fp.GetOrientationDegrees()))
        for p in fp.Pads():
            drill=p.GetDrillSize();x,y=xy(p.GetPosition());hole=None
            if drill.x and drill.y:
                hole={"x":x,"y":y,"diameter":k.ToMM(min(drill.x,drill.y)),"longAxis":k.ToMM(max(drill.x,drill.y))}
                result["holes"].append(hole)
            if p.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            for layer,side in ((k.F_Cu,"front"),(k.B_Cu,"back")):
                if not p.IsOnLayer(layer):continue
                outline=p.GetEffectivePolygon(layer)
                for i in range(outline.OutlineCount()):
                    pp=points(outline.COutline(i))
                    if len(pp)>=3: result["pads"].append({"sides":[side],"polygon":pp,"drill":hole})
    return result
data={s:h for s in ['left','right'] if (h:=hand(s)) is not None}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(data,separators=(",",":"))+"\n")
print("Native copper layers:",", ".join(f"{s}: {len(v['tracks'])} traces; origin residual {v['maxSwitchCenterResidual']:.5f} mm" for s,v in data.items()) or "not available")
