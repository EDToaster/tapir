"""Tapir Rev A per-hand circuit. Pin numbers are PCB pad numbers, not GPIO indices.

Run with Python 3. This writes reviewed component/net intent independently of
physical placement so the schematic and PCB can be compared by native KiCad.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "tapir-reva/" + name))

def circuit(hand):
    out = []
    def add(ref, value, fp, pins):
        out.append(dict(ref=ref, value=value, footprint="Tapir:" + fp,
                        uuid=uid(f"{hand}/{ref}"),
                        pins={str(n):dict(name=name,net=net,type=t) for n,(name,net,t) in pins.items()}))
    for n in range(1, 25 if hand == "left" else 22):
        row,col = divmod(n-1,6) if n<=18 else (3,n-16 if n<=21 else n-22)
        inter=f"K{n:02}"; mouse=n>=22
        add(f"SW{n}", "PTS810SJM250SMTR LFS" if mouse else "CPG135001D01",
            "SW_SPST_PTS810" if mouse else "Choc_PG1350",
            {1:("1",f"COL{col}","passive"),2:("2",inter,"passive")})
        add(f"D{n}","1N4148WS-7-F","D_SOD-323",{1:("K",f"ROW{row}","passive"),2:("A",inter,"passive")})
    gpio_names=["D"+str(i) for i in range(11)]+["3V3","GND","VBUS"]+[
        "D"+str(i) for i in range(11,20)]+["SWDIO","SWDCLK","nRESET","GND_TP","BAT+","BAT-"]
    nets = {**{i+1:f"ROW{i}" for i in range(4)}, **{i+5:f"COL{i}" for i in range(6)},
            13:"GND",27:"GND",28:"VBAT_SW",29:"GND"}
    if hand=="right":
        nets.update({11:"PS2_DATA",12:"3V3",15:"PS2_CLK",16:"PS2_RST",17:"PTR_EN"})
    ptypes={12:"power_out",13:"power_in",14:"power_in",24:"bidirectional",25:"input",26:"input",27:"passive",28:"power_in",29:"passive"}
    add("U1","XIAO nRF52840 Plus","XIAO-nRF52840-Plus-SMD",
        {i:(name,nets.get(i),ptypes.get(i,"bidirectional")) for i,name in enumerate(gpio_names,1)})
    add("J1","S2B-PH-SM4-TB(LF)(SN)","JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
        {1:("BAT+","CELL_PLUS","passive"),2:("BAT-","GND","passive"),"MP":("SHIELD",None,"passive")})
    # PCM12 pin 2 (wiper) goes to the protected cell. The unused throw is always insulated.
    add("S1","PCM12SMTR","SW_SPDT_PCM12",
        {1:("ON","VBAT_SW","passive"),2:("COM","CELL_PLUS","passive"),3:("OFF",None,"passive")})
    if hand=="right":
        add("J2","SK8707-01-004 host cable","Sprintek_Host_Wires",
            {1:("GND","GND","power_in"),2:("DATA","PS2_DATA","bidirectional"),
             3:("CLK","PS2_CLK","bidirectional"),4:("RESET","PS2_RST","input"),5:("VCC","PTR_3V3","power_in")})
        add("U2","TPS22918DBVR","SOT-23-6",
            {1:("VIN","3V3","power_in"),2:("GND","GND","power_in"),3:("ON","PTR_EN","input"),
             4:("CT",None,"passive"),5:("QOD","PTR_3V3","passive"),6:("VOUT","PTR_3V3","power_out")})
        for ref,value,a,b in [("R1","4.7k","PTR_3V3","PS2_DATA"),("R2","4.7k","PTR_3V3","PS2_CLK"),
                              ("R3","100k","PTR_EN","GND"),("C1","1uF","3V3","GND"),("C2","100nF","PTR_3V3","GND")]:
            add(ref,value,("R" if ref[0]=="R" else "C")+"_0603_1608Metric",
                {1:("1",a,"passive"),2:("2",b,"passive")})
    return {"hand":hand,"title":f"Tapir Rev A | {hand.title()} carrier","components":out}

if __name__=="__main__":
    for hand in ("left","right"):
        base=ROOT/"build"/hand; base.mkdir(parents=True,exist_ok=True)
        (base/"design.json").write_text(json.dumps(circuit(hand),indent=2)+"\n")
