#!/usr/bin/python3
"""Add GND return fills to a fully hard-routed PCB. Does not repair open nets.

Refuses to overwrite the input. Keepout extends well beyond the physical antenna
for new planes (distinct from the central no-track/no-via RF screen). Leaves
carrier lands unchanged and deletes isolated copper islands.
"""
import argparse
import json
from pathlib import Path
import pcbnew as k
from design import ROOT,uid
from place_board import GEOMETRY,rotate,xy,zone

def add(hand,path,dest):
    if path.resolve()==dest.resolve():raise ValueError("Input/output must differ")
    board=k.LoadBoard(str(path.resolve())); geom=json.loads(GEOMETRY.read_text())["halves"][hand]
    if any(not z.GetIsRuleArea() for z in board.Zones()):raise ValueError("Existing planes need manual review")
    if not list(board.GetTracks()):raise ValueError("No routed copper")
    module=geom["components"]["xiao"]
    local=[(-12.5,5.8),(12.5,5.8),(12.5,16.5),(-12.5,16.5)]
    pts=[rotate(x,y,module["a"]) for x,y in local]
    zone(board,"Antenna end - extra wide return-plane exclusion",
         [(x+module["x"],y+module["y"]) for x,y in pts],k.LSET.ExternalCuMask(),
         tracks=False,vias=False,pads=False,fill=True)
    for layer in (k.F_Cu,k.B_Cu):
        z=k.ZONE(board);board.Add(z);z.SetLayer(layer);z.SetNet(board.FindNet("GND"))
        z.SetZoneName("GND return "+board.GetLayerName(layer));z.SetUuid(k.KIID(uid(hand+z.GetZoneName())))
        z.SetLocalClearance(k.FromMM(.30));z.SetMinThickness(k.FromMM(.25))
        z.SetPadConnection(k.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        outline=z.Outline();outline.NewOutline()
        for x,y in geom["outline"]:outline.Append(xy(x,y))
    # Existing traces provide GND continuity; do not rely on islands/traces
    # which merely touch in the filled-copper rendering.
    board.BuildConnectivity()
    if not k.ZONE_FILLER(board).Fill(board.Zones()):raise RuntimeError("Zone fill failed")
    if not k.SaveBoard(str(dest.resolve()),board,True):raise OSError(dest)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("hand",choices=["left","right"]);p.add_argument("input",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();add(a.hand,a.input,a.output)
