"""Independent placement, electrical and logical expectations; never import the product generators."""
import hashlib
import itertools
import json
import math
import re

from native import Blocked, contour_residual, point_segment


def demand(ok,msg):
    if not ok:
        raise ValueError(msg)


def expected(hand):
    parts={}
    for n in range(1,25 if hand=="left" else 22):
        r,c=divmod(n-1,6) if n<=18 else (3,n-16 if n<=21 else n-22)
        k=f"K{n:02d}"
        parts[f"SW{n}"]={"1":f"COL{c}","2":k}
        parts[f"D{n}"]={"1":f"ROW{r}","2":k}
    parts["U1"]={**{str(i+1):f"ROW{i}" for i in range(4)},
                 **{str(i+5):f"COL{i}" for i in range(6)},
                 "13":"GND","27":"GND","28":"VBAT_SW","29":"GND"}
    parts["J1"]={"1":"CELL_PLUS","2":"GND"}
    parts["S1"]={"1":"VBAT_SW","2":"CELL_PLUS"}
    if hand=="right":
        parts["U1"].update({"11":"PS2_DATA","12":"3V3","15":"PS2_CLK","16":"PS2_RST","17":"PTR_EN"})
        parts.update({"J2":dict(zip("12345",["GND","PS2_DATA","PS2_CLK","PS2_RST","PTR_3V3"])),
            "U2":dict(zip("12356",["3V3","GND","PTR_EN","PTR_3V3","PTR_3V3"])),
            "R1":{"1":"PTR_3V3","2":"PS2_DATA"},"R2":{"1":"PTR_3V3","2":"PS2_CLK"},
            "R3":{"1":"PTR_EN","2":"GND"},"C1":{"1":"3V3","2":"GND"},
            "C2":{"1":"PTR_3V3","2":"GND"}})
    return parts


def endpoints(ep,hand):
    pts={(r,p):n for r,pins in expected(hand).items() for p,n in pins.items()}
    diff=[f"{r}.{p}: {ep.get((r,p))} != {pts.get((r,p))}" for r,p in sorted(set(pts)|set(ep))
          if ep.get((r,p))!=pts.get((r,p))]
    demand(not diff,"; ".join(diff))
    return f"{len(ep)} functional pin/net endpoints on {len(expected(hand))} electrical designators match independent matrix, power and controller contract"


def global_pad(f,p):
    a=math.radians(-f["angle"])
    dx,dy=p["local"]
    return (f["xy"][0]-100+dx*math.cos(a)-dy*math.sin(a),
            f["xy"][1]-100+dx*math.sin(a)+dy*math.cos(a))


def placement(board,h):
    residual=[]
    for s in h["switches"]+h["buttons"]:
        ref=s["ref"]; f=board.parts[ref]; x,y=s["x"],s["y"]
        residual.append((math.dist(f["xy"],[100+x,100+y]),ref))
        if s in h["switches"]:
            demand(len(f["pads"])==len(s["pins"]),f"{ref} pad count changed")
        else:
            demand(len(f["pads"])==len(s["pads"]),f"{ref} tactile contact count changed")
        pool=list(f["pads"])
        for pin in s.get("pins",s.get("pads",[])):
            pid=str(pin.get("pin",pin.get("id")))
            pads=[(math.dist(global_pad(f,p),[pin["x"],pin["y"]]), i, p)
                  for i,p in enumerate(pool) if p["pin"]==(pid if pid.isdigit() else "")]
            demand(pads,f"{ref} missing {pid}")
            d,i,p=min(pads,key=lambda x:x[0]); pool.pop(i)
            residual.append((d,f"{ref}.{pid} XY"))
            if "drill" in pin:
                demand(len(p["drill"])==1 and (p["kind"]=="np_thru_hole")== (pin["type"]=="NPTH"),
                       f"{ref}.{pid} not expected plated/NPTH round drill")
                residual.append((abs(p["drill"][0]-pin["drill"]),f"{ref}.{pid} Ø"))
        d=s["diode"]; f=board.parts[d["id"]]
        residual.append((math.dist(f["xy"],[100+d["x"],100+d["y"]]),d["id"]))
        demand(f["layer"]=="B.Cu",f"{d['id']} diode not on underside")
    worst=max(residual)
    demand(worst[0]<=0.015,f"{worst[1]} offset/dimension {worst[0]:.6f} mm >0.015")
    return f"{len(residual)} native XY/drill comparisons (including asymmetric Choc locators and backside diodes); max residual {worst[0]:.6f} mm ({worst[1]}); tolerance 0.015 mm"


def outline(board,h):
    pts=[(100+x,100+y) for x,y in h["outline"]]
    actual=board.outline()
    exp=list(zip(pts,pts[1:]+pts[:1]))
    d=contour_residual(exp,actual)
    area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in exp))/2
    # Endpoints degree two is necessary for closure; DRC separately checks board validity.
    degrees={}
    for a,b in actual:
        for p in [a,b]:
            key=tuple(round(v,5) for v in p)
            degrees[key]=degrees.get(key,0)+1
    demand(all(x==2 for x in degrees.values()),"non-closed outline endpoints")
    dims=[max(p[k] for p in pts)-min(p[k] for p in pts) for k in range(2)]
    demand(d<=0.015 and abs(board.thickness-h["pcb"]["thickness"])<=0.01 and dims[0]<=135 and dims[1]<=107,
           f"outline residual {d:.6f} mm, {board.thickness} mm thickness, bounds {dims}")
    return f"{len(actual)} native edges, {dims[0]:.3f} × {dims[1]:.3f} × {board.thickness:.2f} mm, {area:.2f} mm²; bidirectional contour sample residual {d:.6f} mm"


def holes(board,h):
    ds=[]
    for hole in h["mountingHoles"]:
        f=board.parts[hole["ref"]]
        p,=[p for p in f["pads"] if p["kind"]=="np_thru_hole"]
        ds.append((math.dist(global_pad(f,p),[hole["x"],hole["y"]]),abs(p["drill"][0]-hole["diameter"])))
    demand(len(ds)>=3 and max(max(k) for k in ds)<=0.015,f"mount residuals XY, Ø: {ds}")
    return f"{len(ds)} native NPTHs vs boss datums; maximum XY {max(x for x,y in ds):.6f} mm, Ø {max(y for x,y in ds):.6f} mm. This does not establish printed boss fit."


def every_drill(board,h):
    pools={}
    for ref,f in board.parts.items():
        for p in f["pads"]:
            if not p["drill"]: continue
            demand(len(p["drill"])==1,f"{ref} contains unsupported slot")
            pools.setdefault(ref,[]).append((global_pad(f,p),p["drill"][0],p["kind"]))
    n=sum(map(len,pools.values())); checks=[]
    demand(n==len(h["holes"]),f"native footprint drills {n} vs declared {len(h['holes'])}")
    for g in h["holes"]:
        ref=g["owner"] if g["owner"]!="carrier" else g["id"]
        choice=[(math.dist(p,[g["x"],g["y"]]),abs(d-g["drill"]),i) for i,(p,d,k) in enumerate(pools[ref]) if
                (k=="np_thru_hole")==(g["type"]=="NPTH")]
        demand(choice,f"no native perforation for {g['id']}")
        dx,dd,i=min(choice);pools[ref].pop(i); checks.append((dx,dd))
    mxy=max(a for a,b in checks); md=max(b for a,b in checks)
    demand(max(mxy,md)<0.015,f"drill residual XY {mxy}, diameter {md}")
    return f"{n}/{n} footprint drills one-to-one by owning reference, plating, coordinate and Ø; maximum XY {mxy:.6f} mm, Ø {md:.6f} mm. Includes switch, slide, mount and any wire-pad holes; routing vias excluded."


def span(s):
    p=s["polygon"]
    return [max(a[i] for a in p)-min(a[i] for a in p) for i in (0,1)]+[s["top"]-s["bottom"]]


def battery(h):
    c=h["components"]
    dims=span(c["battery"]); reserve=span(c["batteryReserve"])
    nominal=[11.5,31,3.8]; maximum=[12.3,32,4.3]; rem=[m-n for m,n in zip(reserve,maximum)]
    demand(all(abs(a-b)<0.02 for a,b in zip(dims,nominal)),f"incorrect product 1570 body: {dims}")
    demand(all(x>0 for x in rem),f"reserve {reserve} does not contain drawing max {maximum}")
    demand("S2B-PH-SM4" in c["batteryConnector"]["label"] and "PCM12" in c["powerSwitch"]["label"],"incorrect selected connector or switch")
    return (f"body {dims[0]:.1f}×{dims[1]:.1f}×{dims[2]:.1f} mm, reserve {reserve[0]:.1f}×{reserve[1]:.1f}×{reserve[2]:.1f} vs max cell 12.3×32×4.3. Remaining total XYZ {rem[0]:.2f}/{rem[1]:.2f}/{rem[2]:.2f} mm is not approved swell/lead/insulation space.")


def clearance(a,b):
    x,y=a["polygon"],b["polygon"]
    def edges(p):
        return list(zip(p,p[1:]+p[:1]))
    def projections(p,axis):
        v=[sum(u*w for u,w in zip(q,axis)) for q in p]
        return min(v),max(v)
    gaps=[]
    for u,v in edges(x)+edges(y):
        dx,dy=v[0]-u[0],v[1]-u[1]; norm=math.hypot(dx,dy)
        if norm<1e-10:
            continue
        axis=(-dy/norm,dx/norm)
        ll,lr=projections(x,axis); rl,rr=projections(y,axis)
        gaps.append(max(ll-rr,rl-lr))
    xy=max(gaps)
    if xy>0:
        xy=min([point_segment(p,e) for p in x for e in edges(y)]+
               [point_segment(p,e) for p in y for e in edges(x)])
    z=max(a["bottom"]-b["top"],b["bottom"]-a["top"])
    return math.hypot(max(0,xy),max(0,z)) if max(xy,z)>0 else max(xy,z)


def sweep(h):
    strokes=[s for s in h["solids"] if s["role"]=="key-sweep"]
    demand(len(strokes)==21,"not 21 swept key envelopes")
    obs=[s for s in h["solids"] if s["role"] in ("sensor","bridge","support","controller","driver",
         "battery-reserve","power-switch","battery-connector","stick-cap","button-paddle","usb-plug")]
    pairs=list(itertools.combinations(strokes,2))+list(itertools.product(strokes,obs))
    rows=[(clearance(a,b),a["id"],b["id"]) for a,b in pairs]
    v,a,b=min(rows)
    demand(v>0,f"interference {a}/{b} {v:.4f} mm, {sum(r[0]<=0 for r in rows)} conflicts")
    return f"{len(pairs)} pairwise convex prism checks across all 21 full-stroke unions (including rest and bottom-out); closest {a} to {b}: +{v:.3f} mm; nominal, no tolerance or flex"


REFERENCE = {"def":"de5c89e7c9cff46bd92d6e134a6a8576330cc7541f834b36a49e352156c60384",
             "nav":"cab28afc65f481b6c5d531709407d56bc846ca1eba0f621b7a40490e96613590",
             "num":"e2ee538279db14f709f1bd8897e410c1e6244c1fb9f4ee301f5b332022d58f79"}


def read_clean(path):
    return re.sub(r'/\*.*?\*/|//[^\n]*',' ',path.read_text(),flags=re.S)


def mapcheck(dts):
    rows=[(int(a),int(b)) for a,b in re.findall(r'RC\(\s*(\d+)\s*,\s*(\d+)\s*\)',dts)]
    corr=[(r,c) for r in range(3) for c in range(12)]+[(3,c) for c in [3,4,5,6,7,8,0,1,2]]
    demand(rows==corr,"45-position firmware transform differs from Corne-42 + left 3")
    return rows


def layercheck(s):
    for label,sha in REFERENCE.items():
        match=re.search(r'\b'+label+r'\s*\{[^}]*bindings\s*=\s*<([^>]+)>',s,re.S)
        demand(match,f"missing {label} layer")
        bindings=[' '.join(z.split()) for z in re.findall(r'&[^&]+',match[1])]
        sig=hashlib.sha256(json.dumps(bindings[:42],separators=(',',':')).encode()).hexdigest()
        demand(sig==sha and len(bindings)==45,f"{label} first 42 differ or wrong layer length")
        demand(bindings[42:]==(["&mkp LCLK","&mo 3","&mkp RCLK"] if label=="def" else ["&trans"]*3),
               f"{label} mouse assignments incorrect")
    holds=re.findall(r'hold-trigger-key-positions\s*=\s*<([^>]+)>',s)
    demand(len(holds)==2 and all(0<=int(i)<42 for group in holds for i in group.split()),"stale hold-trigger position")
    return "126/126 original bindings match normalized frozen keymap SHA on Base/Lower/Raise; 3 appended controls match, none silently trigger original hold-taps"


def topology(h,ep,dts,overlay,hand):
    logical=mapcheck(dts)
    def rowprop(s,prop):
        m=re.search(prop+r'\s*=\s*([^;]*);',s,re.S)
        return [int(x) for x in re.findall(r'&xiao_d\s+(\d+)', m[1])] if m else []
    rows=rowprop(dts,"row-gpios"); cols=rowprop(overlay,"col-gpios")
    demand(rows==[0,1,2,3] and len(cols)==6 and 'diode-direction = "col2row"' in dts,"row/column scan or diode polarity not recognized")
    off=re.search(r'col-offset\s*=\s*<(\d+)>',overlay); off=int(off[1]) if off else 0
    out=[]
    for s in h["switches"]+h["buttons"]:
        ref=s["ref"]; n=int(ref[2:]); diode="D"+str(n)
        row,col=s["row"],s["col"]
        demand(ep[(ref,"2")]==ep[(diode,"2")]==f"K{n:02}",f"{ref} switched net")
        rowpin,=[i for i in rows if ep.get(("U1",str(i+1)))==ep[diode,"1"]]
        colpin,=[i for i in cols if ep.get(("U1",str(i+1)))==ep[ref,"1"]]
        r,c=rows.index(rowpin),cols.index(colpin)+off
        want=(row,col if hand=="left" else 11-col)
        demand((r,c)==want and (r,c) in logical,f"{ref}: {r,c} != {want}")
        out.append(dict(ref=ref,label=s["label"],logical=logical.index((r,c)),global_matrix=[r,c],
                        x=s["x"],y=s["y"],row_gpio=f"D{rowpin}",column_gpio=f"D{colpin}"))
    demand(len(set(o["logical"] for o in out))==len(out),"aliased physical position")
    return out
