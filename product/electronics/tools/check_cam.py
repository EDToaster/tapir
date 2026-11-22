#!/usr/bin/env python3
"""Independent engineering-preview CAM parser; install gerbonara==1.6.3.

Reads the 9 actual RS-274X/X2 plots and 2 Excellon files. Compares the entire
drill register and every named copper-land flash against native KiCad pads,
as well as every profile centerline against the common mechanical datum.
This is a digital file-integrity gate, not an electrical test or fab approval.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def truth(hand):
    import pcbnew as k
    b=k.LoadBoard(str(ROOT/hand/f"tapir-{hand}.kicad_pcb"))
    out={"PTH":[],"NPTH":[],"F_Cu":[],"B_Cu":[]}
    for f in b.GetFootprints():
        for p in f.Pads():
            x,y=(v/1e6 for v in p.GetPosition());d=p.GetDrillSize()
            if d.x:
                if d.x!=d.y:raise ValueError("Nonround drill needs slot-aware review")
                out['NPTH' if p.GetAttribute()==k.PAD_ATTRIB_NPTH else 'PTH'].append([x,-y,d.x/1e6])
            if p.GetNumber():
                for s,layer in [('F_Cu',k.F_Cu),('B_Cu',k.B_Cu)]:
                    if p.IsOnLayer(layer):
                        out[s].append([f.GetReference(),p.GetNumber(),x,-y,p.GetNetname()])
    for t in b.GetTracks():
        if t.Type()==k.PCB_VIA_T:
            x,y=(v/1e6 for v in t.GetPosition());out['PTH'].append([x,-y,t.GetDrillValue()/1e6])
    return out
def validate(hand,dest):
    from gerbonara import GerberFile,ExcellonFile
    from gerbonara.graphic_objects import Flash,Line
    from importlib.metadata import version
    plots=dest/'layers-and-drills';stem=f'tapir-{hand}'
    native=json.loads(subprocess.check_output(['/usr/bin/python3',__file__,hand,'--native'],text=True))
    msg={"parser":"Gerbonara "+version('gerbonara'),"scope":"Digital geometry/net-attribute readback; no fabricated part measured.",
         "layers":{},"drills":{},"copper_lands":{}}
    layers={"F_Cu":"Copper,L1,Top","B_Cu":"Copper,L2,Bot","F_Mask":"Soldermask,Top","B_Mask":"Soldermask,Bot",
            "F_Silkscreen":"Legend,Top","B_Silkscreen":"Legend,Bot","F_Paste":"Paste,Top","B_Paste":"Paste,Bot","Edge_Cuts":"Profile,NP"}
    if set(plots.glob("*.gbr"))!={plots/f"{stem}-{s}.gbr" for s in layers}:raise ValueError("Unexpected Gerber set")
    for suffix,ident in layers.items():
        g=GerberFile.open(plots/f'{stem}-{suffix}.gbr');tag=','.join(g.file_attrs['.FileFunction'])
        if tag!=ident or not g.objects:raise ValueError(f"Malformed or empty {suffix}")
        msg["layers"][suffix]={"function":tag,"objects":len(g.objects)}
        if suffix in ('F_Cu','B_Cu'):
            entries=[]
            for o in g.objects:
                if isinstance(o,Flash) and '.P' in o.attrs and len(o.attrs['.P'])>=2 and o.attrs['.P'][1]:
                    r,n,*_=o.attrs['.P'];entries.append((r,n,round(o.x,6),round(o.y,6),o.attrs.get('.N',('',))[0]))
            expected=sorted((r,n,round(x,6),round(y,6),net) for r,n,x,y,net in native[suffix])
            if sorted(entries)!=expected:
                raise ValueError(f"{suffix} copper flash/position/net differs: {set(expected)-set(entries)}; unexpected: {set(entries)-set(expected)}")
            msg["copper_lands"][suffix]={"all_numbered_pads_matched":len(expected)}
        if suffix=='Edge_Cuts':
            points=json.loads((ROOT.parent/'design/geometry.json').read_text())['halves'][hand]['outline']
            def edge(a,b):return tuple(sorted((tuple(a),tuple(b))))
            pts=[(100+x,-100-y) for x,y in points]
            expected=sorted(edge(v,pts[(i+1)%len(pts)]) for i,v in enumerate(pts))
            actual=sorted(edge((o.x1,o.y1),(o.x2,o.y2)) for o in g.objects if isinstance(o,Line))
            e=max((abs(x-y) for A,B in zip(expected,actual) for a,b in zip(A,B) for x,y in zip(a,b)),default=0)
            if len(expected)!=len(actual) or len(actual)!=len(g.objects) or e>.000002:raise ValueError('Fabrication profile differs from geometry.json')
            msg["profile_segments_matched"]=len(actual)
            msg["profile_max_coordinate_error_mm"]=round(e,6)
    for kind in ('PTH','NPTH'):
        f=ExcellonFile.open(plots/f'{stem}-{kind}.drl',plated=kind=='PTH');pending=native[kind].copy();errors=[]
        for o in f.objects:
            if not isinstance(o,Flash):raise ValueError("Non-round drill hit needs manual review")
            hit=(o.x,o.y,o.aperture.diameter)
            if not pending:raise ValueError(f"Unexpected {kind} extra drill")
            i=min(range(len(pending)),key=lambda i:max(abs(a-b) for a,b in zip(hit,pending[i])))
            e=max(abs(a-b) for a,b in zip(hit,pending.pop(i)));errors.append(e)
            if e>.000501:raise ValueError(f"Unmatched {kind} drill/position at {hit} (error {e} mm)")
        if pending:raise ValueError(f"Missing {kind} drill(s): {pending}")
        msg["drills"][kind]={"hits":len(errors),"max_xyz_or_dia_rounding_mm":round(max(errors),6)}
    msg["pass"]=True
    return msg
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('hand',choices=['left','right']);p.add_argument('--native',action='store_true');p.add_argument('--dir',type=Path);p.add_argument('--save-to',type=Path);a=p.parse_args()
    if a.native:print(json.dumps(truth(a.hand)))
    else:
        dest=a.dir or ROOT/'build'/'fabrication'/a.hand
        msg=validate(a.hand,dest);print(json.dumps(msg,indent=2))
        if a.save_to:
            a.save_to.write_text(json.dumps(msg,indent=2)+'\n')
            (ROOT/'reports'/f'tapir-{a.hand}-cam-readback.json').write_text(json.dumps(msg,indent=2)+'\n')
