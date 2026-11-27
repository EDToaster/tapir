#!/usr/bin/python3
"""Generate unrouted boards in build/<hand>. Never overwrites the routed sources.

XY = mechanical coordinates + (100,100) mm, for both independent hands. This
is a translation only. KiCad positive rotation is counterclockwise looking down.
"""
import argparse
import json
import math
from pathlib import Path
import pcbnew as k
from design import ROOT,circuit,uid
from project import create

LIB=ROOT/"Tapir.pretty"
GEOMETRY=ROOT.parent/"design"/"geometry.json"
def xy(x,y):return k.VECTOR2I(k.FromMM(100+x),k.FromMM(100+y))
def mm(s):return k.FromMM(s)
def xyof(obj):return obj["x"],obj["y"]
def rotate(x,y,a):
    a=math.radians(a); return x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)
def zone(b,name,polygon,layers,tracks=True,vias=True,pads=True,fill=True,footprints=False):
    z=k.ZONE(b);b.Add(z);z.SetIsRuleArea(True);z.SetZoneName(name);z.SetLayerSet(layers)
    z.SetDoNotAllowTracks(tracks);z.SetDoNotAllowVias(vias);z.SetDoNotAllowPads(pads)
    z.SetDoNotAllowZoneFills(fill);z.SetDoNotAllowFootprints(footprints)
    loop=z.Outline();loop.NewOutline()
    for x,y in polygon:loop.Append(xy(x,y))
    z.SetUuid(k.KIID(uid(name+str(polygon))))
def line(b,v1,v2,layer,width,tag):
    s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(xy(*v1));s.SetEnd(xy(*v2))
    s.SetLayer(layer);s.SetWidth(mm(width));s.SetUuid(k.KIID(uid(tag)));b.Add(s)
def label(b,text,x,y,layer,size=.85,angle=0):
    s=k.PCB_TEXT(b);s.SetText(text);s.SetPosition(xy(x,y));s.SetLayer(layer)
    s.SetTextSize(k.VECTOR2I(mm(size),mm(size)));s.SetTextThickness(mm(max(.12,size*.15)))
    s.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T));s.SetMirrored(layer==k.B_SilkS)
    s.SetUuid(k.KIID(uid(text+str((x,y,layer)))));b.Add(s)

def build(hand):
    assert k.GetBuildVersion().startswith("10."), "Use KiCad 10's system Python"
    create(hand)
    g=json.loads(GEOMETRY.read_text())["halves"][hand];com=g["components"];src=circuit(hand)
    intent={c["ref"]:c for c in src["components"]};stem=f"tapir-{hand}";out=ROOT/"build"/hand
    b=k.BOARD(); b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(mm(1.60))
    b.SetFileName(str(out/(stem+".kicad_pcb"))); nets={}
    for i,p in enumerate(g["outline"]):
        q=g["outline"][(i+1)%len(g["outline"])]
        if p!=q:line(b,p,q,k.Edge_Cuts,.05,f"{hand}/outline/{i}")
    def fp(ref,x,y,angle=0,back=False,mech=False,footprint=None):
        c=intent.get(ref,{});name=footprint or c["footprint"].split(":",1)[1]
        f=k.FootprintLoad(str(LIB),name)
        if not f:raise ValueError("Unreadable footprint "+name)
        f.SetFPIDAsString("Tapir:"+name);f.SetReference(ref);f.SetValue(c.get("value",name))
        f.SetUuid(k.KIID(uid(f"{hand}/pcb/{ref}")))
        if not mech:
            f.SetPath(k.KIID_PATH("/"+c["uuid"]));f.SetSheetfile(stem+".kicad_sch");f.SetSheetname("/")
        else:f.SetAttributes(f.GetAttributes()|k.FP_BOARD_ONLY|k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES)
        b.Add(f)  # KiCad 10 Flip() requires an owning board for its layer stack.
        if back:f.Flip(k.VECTOR2I(0,0),k.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(angle);f.SetPosition(xy(x,y))
        # PCB has separate assembly-marking text: hide automatic references to
        # avoid silk inside key housings. Fab references/values stay editable.
        f.Reference().SetVisible(False)
        for i,pad in enumerate(f.Pads()):
            pad.SetUuid(k.KIID(uid(f"{hand}/pcb/{ref}/pad/{i}")))
            n=pad.GetNumber()
            if not n or mech:continue
            pin=c["pins"][n];pad.SetPinFunction(pin["name"]);pad.SetPinType(pin["type"])
            net=pin["net"]
            if net is None:net=f"unconnected-({ref}-{pin['name']}-Pad{n})"
            if net not in nets:
                nets[net]=k.NETINFO_ITEM(b,net);b.Add(nets[net])
            pad.SetNet(nets[net])
        return f

    for s in g["switches"]+g["buttons"]:
        fp(s["ref"],s["x"],s["y"],-s["a"])
        d=s["diode"];fp(d["id"],d["x"],d["y"],-d["a"],True)
    for ref,name in (("U1","xiao"),("S1","powerSwitch"),("J1","batteryConnector")):
        p=com[name];fp(ref,p["x"],p["y"],(90 if ref=="U1" else 0)-p["a"])
    if hand=="right":
        q=com["driverHeader"];fp("J2",q["x"],q["y"],-q["a"])
        for p in com["driverDiscrete"]:
            fp(p["ref"],p["x"],p["y"],-p["a"])
    allCu=k.LSET.ExternalCuMask();front=k.LSET();front.AddLayer(k.F_Cu)
    for h in g["mountingHoles"]:
        ref=h["ref"];x,y=xyof(h)
        fp(ref,x,y,mech=True,footprint="M2_Carrier_Mount")
        rad=h["bossDiameter"]/2
        # Four sectors form a continuous annulus; its central opening contains
        # *only* the NPTH. The global copper/hole rule already protects that
        # hole and the 0.10 mm gap. Thus disallowing pads includes SMD copper
        # as intended without flagging the mounting hole as its own violation.
        for sector in range(4):
            angles=[(sector*8+i)*math.pi/16 for i in range(9)]
            polygon=[(x+rad*math.cos(a),y+rad*math.sin(a)) for a in angles]
            polygon += [(x+1.2*math.cos(a),y+1.2*math.sin(a)) for a in reversed(angles)]
            zone(b,ref+f" M2 fastener - keep copper out ({sector})",polygon,allCu)
    # Provisional RF screen in canonical geometry, across both copper layers.
    # The two factory battery lands necessarily encroach at its inboard edge.
    # Block *new conductors* within the entire screen; pad exception is
    # documented and must be measured on the physical module.
    zone(b,"XIAO antenna screen - no tracks, vias or planes; module pads retained",com["antennaScreen"]["polygon"],allCu,pads=False)
    if hand=="right":
        for p in com["feet"]:
            zone(b,p["id"]+" carrier bridge landing",p["polygon"],front,tracks=False,fill=False)
        zone(b,"Sprintek detached driver insulated mounting site",com["driver"]["polygon"],front,tracks=False,fill=False)
    zone(b,"Pouch nonconductive bed - no pads or vias under pouch",com["batteryReserve"]["polygon"],front,tracks=False,fill=False)
    # Place discrete inspection/assembly legends on fabrication drawing. Operator
    # also gets solder-side board identity. Do not mark switch ON/OFF until its
    # wiper travel direction has been physically checked.
    for ref,name in (("J1","batteryConnector"),("S1","powerSwitch"),("U1","xiao")):
        p=com[name];label(b,ref+" "+intent[ref]["value"],p["x"],p["y"],k.Cmts_User,.75)
    tx,ty=(22.8,15.5) if hand=="left" else (55,40)
    label(b,"TAPIR  /  "+hand.upper()+"  /  A",tx,ty,k.B_SilkS,1.25,90 if hand=="left" else 0)
    if hand=="right":
        label(b,"1:G  2:D  3:C  4:R  5:V",50,51.25,k.B_SilkS,.8)
    b.BuildConnectivity()
    f=out/(stem+".kicad_pcb")
    if not k.SaveBoard(str(f),b,True): raise OSError(f)
    print(f,"footprints",len(list(b.GetFootprints())),"nets",len(nets))
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("hands",nargs="*",default=["left","right"])
    for h in p.parse_args().hands: build(h)
