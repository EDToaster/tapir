"""Read native AP214 assembly occurrence transforms; no CAD producer API or templates."""
from collections import Counter
from pathlib import Path
from itertools import product
import hashlib
import json
import math
import re
from contracts import demand
from native import Board


def extract(step):
    t={int(n):" ".join(v.split()) for n,v in re.findall(r'^#(\d+)\s*=\s*(.*?);',step.read_text(),re.M|re.S)}
    ids=lambda v:list(map(int,re.findall(r'#(\d+)',v)))
    via={}; ctx={};nodes={}
    for n,v in t.items():
        if v.startswith("PRODUCT_DEFINITION_SHAPE('Placement'"): via[ids(v)[-1]]=n
        elif v.startswith("CONTEXT_DEPENDENT_SHAPE_REPRESENTATION("):
            a,b=ids(v);ctx[b]=a
        elif v.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE("):
            pairs=re.findall("'([^']*)'",v);a,b=ids(v)
            nodes[n]=(pairs[1],a,b)
    root=Counter(a for label,a,b in nodes.values() if re.fullmatch(r'(?:[A-Z]+)\d+',label)).most_common(1)[0][0]
    out=[]
    def vector(e):
        return tuple(float(i) for i in re.search(r'\(([-+\d.Ee, ]+)\)\)',e)[1].split(","))
    for n,(label,a,b) in nodes.items():
        if a!=root: continue
        pdef,=ids(t[b])[:1]; product,=ids(t[pdef])[:1]
        model=re.search(r"PRODUCT\('([^']+)'",t[product])[1]
        tx=int(re.search(r'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION\(#(\d+)\)',t[ctx[via[n]]])[1])
        axis=ids(t[tx])[-1];o,z,x=ids(t[axis])
        out.append(dict(ref=label,model=model,pos=vector(t[o]),up=vector(t[z]),across=vector(t[x])))
    return out


def compare(board,step):
    brd=Board(board); occurrences=extract(step); actual=Counter(); requested=Counter(); deviation=[]
    model_dir=board.parent.parent/"models"; manifest=json.loads((model_dir/"manifest.json").read_text())
    classifications={}; bounds=[float('inf')]*3+[-float('inf')]*3
    board_occ=[v for v in occurrences if v["model"].endswith("_PCB")]
    demand(len(board_occ)==1,"native STEP has no unique carrier solid")
    for ref,p in brd.parts.items():
        for source in p["models"]:
            requested[(ref,Path(source).stem)]+=1
        classifications[ref]=[Path(m).name+": "+manifest[Path(m).name]["fidelity"] for m in p["models"]]
        if not classifications[ref]:
            demand(ref in ("H1","H2","H3","H4","J2"),f"functional component missing a model: {ref}")
            classifications[ref]=["Fabricated hole in carrier; no separate purchased solid." if ref.startswith("H") else
                                  "Bare copper harness pads; no connector solid. Actual interconnect, strain relief and solder are bench-only."]
    for name in {name+".step" for ref,name in requested}:
        demand(hashlib.sha256((model_dir/name).read_bytes()).hexdigest()==manifest[name]["sha256"],f"model library hash mismatch: {name}")
    for o in occurrences:
        if o in board_occ: continue
        actual[(o["ref"],o["model"])]+=1
        p=brd.parts[o["ref"]]; front=p["layer"]=="F.Cu"
        demand(abs(o["up"][2]-(1 if front else -1))<1e-6,f"wrong STEP side for {o['ref']}")
        ang=math.radians(p["angle"])
        demand(math.dist(o["across"],(math.cos(ang),math.sin(ang),0))<.00002,f"wrong STEP yaw {o['ref']}")
        x,y=p["xy"]; px,py,pz=o["pos"]
        deviation.append(math.dist([x-100,-(y-100)],[px,py]))
        if front: demand(abs(pz-1.595)<.0001,f"{o['ref']} top seating plane {pz}")
        else: demand(abs(pz+.085)<.0001,f"{o['ref']} underside seating plane {pz}")
        # Conservative containment of every rotated native model: transform all
        # eight corners of the source's recorded local solid bounds using the
        # occurrence's actual, not its intended, local-to-world frame.
        ax=o["across"];az=o["up"];ay=tuple(az[(i+1)%3]*ax[(i+2)%3]-az[(i+2)%3]*ax[(i+1)%3] for i in range(3))
        m=manifest[o["model"]+".step"]
        for a,b,c in product(*zip(m["bbox_min_mm"],m["bbox_max_mm"])):
            for i in range(3):
                v=o["pos"][i]+a*ax[i]+b*ay[i]+c*az[i]-(1.595 if i==2 else 0)
                bounds[i]=min(bounds[i],v);bounds[i+3]=max(bounds[i+3],v)
    demand(actual==requested,f"STEP missing or extra instances: {dict(requested-actual)}, {dict(actual-requested)}")
    demand(max(deviation)<.015,f"STEP occurrence translation mismatch {max(deviation):.6f} mm")
    return len(occurrences),max(deviation),bounds,classifications
