"""Prepare Tapir.pretty, pin-accurate, self-contained KiCad 10 land patterns.

Normally use the committed library. Run only to refresh it from the documented
vendor ZIP and KiCad 10.0.8 stock libraries. Physical pad geometry is preserved.
"""
import argparse
import hashlib
from pathlib import Path
import re
import zipfile
from design import ROOT, circuit

LIB=ROOT/"Tapir.pretty"
STOCK=Path("/usr/share/kicad/footprints")
FAMILIES={
    "SW_SPST_PTS810":"Button_Switch_SMD", "D_SOD-323":"Diode_SMD", "SW_SPDT_PCM12":"Button_Switch_SMD",
    "SOT-23-6":"Package_TO_SOT_SMD", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal":"Connector_JST",
    "R_0603_1608Metric":"Resistor_SMD", "C_0603_1608Metric":"Capacitor_SMD"}

def field(name,value,x,y,layer):
    return f'(property "{name}" "{value}" (at {x} {y}) (layer "{layer}") (effects (font (size 0.75 0.75) (thickness 0.12))))'
def custom(name,smd,geometry):
    return (f'(footprint "{name}" (version 20260206) (generator "pcbnew") (generator_version "10.0") (layer "F.Cu")\n'
            +field("Reference","REF**",0,0,"F.SilkS")+"\n"+field("Value",name,0,2,"F.Fab")
            +f'\n(attr {smd})\n'+geometry+'\n)\n')
def rect(x0,y0,x1,y1,layer):
    return f'(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width 0.05) (type solid)) (fill none) (layer "{layer}"))\n'
def pad(n,x,y,d,diam=None):
    return (f'(pad "{n}" {"thru_hole" if n else "np_thru_hole"} {"rect" if n=="1" else "circle"} '
            f'(at {x} {y}) (size {diam or d} {diam or d}) (drill {d}) (layers "*.Cu" "*.Mask"))\n')
def model(name):
    return f'(model "${{KIPRJMOD}}/../models/{name}.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
def make(host):
    LIB.mkdir(parents=True,exist_ok=True)
    for name, family in FAMILIES.items():
        original=(STOCK/(family+".pretty")/(name+".kicad_mod")).read_text()
        # Keep original geometry and anchoring, but resolve local models without
        # requiring distribution-specific environment variables / packages.
        original=re.sub(r'\$\{KICAD10_3DMODEL_DIR\}/[^"]+/', '${KIPRJMOD}/../models/', original)
        if name.startswith("JST_PH_"):
            original=original.replace(name+".step","JST_S2B_PH_SM4_TB_fit.step")
        if name=="SW_SPDT_PCM12":
            # The actuator projects beyond the outline deliberately; no ink can
            # be printed there. Move the stock artwork to the assembly drawing.
            start=original.index("\n\t(fp_line")
            original=original[:start]+original[start:].replace('(layer "F.SilkS")','(layer "F.Fab")')
        (LIB/(name+".kicad_mod")).write_text(original)
    if hashlib.sha256(host.read_bytes()).hexdigest()!="671cb119639e489091b87a64e070d4aba1f22860ddfdbecc85ff143c0c295e28":
        raise ValueError("Seeed land pattern ZIP differs from approved revision")
    with zipfile.ZipFile(host) as z:
        mod=z.read("New_XIAO_Series_Footprints/XIAO-nRF52840-Plus-SMD.kicad_mod").decode().replace("\r","")
    # Vendor contains multiple unrelated hidden/visible models, including an
    # enabled SAMD21. Drop them. Silk would also print on module solder lands:
    # move outline graphics to fabrication, preserve pads verbatim.
    mod=mod[:mod.index("\n\t(model ")]
    graphics_at=mod.index("\n\t(fp_line")
    mod=mod[:graphics_at]+mod[graphics_at:].replace('(layer "F.SilkS")','(layer "F.Fab")')
    (LIB/"XIAO-nRF52840-Plus-SMD.kicad_mod").write_text(mod+"\n"+model("XIAO_nRF52840_Plus_nonSense_fit")+")\n")
    choc=rect(-7.5,-7.5,7.5,7.5,"F.Fab")+rect(-7.55,-7.55,7.55,7.55,"F.CrtYd")
    # Match drawing / top view: metal contacts and all three locating posts;
    # fourth small guide is reserved for Choc shell variant compatibility.
    choc+=pad("1",5,-3.8,1.27,2.032)+pad("2",0,-5.9,1.27,2.032)
    choc+=pad("",0,0,3.429)+pad("",-5.5,0,1.7018)+pad("",5.5,0,1.7018)+pad("",-5.22,4.2,.9906)
    (LIB/"Choc_PG1350.kicad_mod").write_text(custom("Choc_PG1350","through_hole",choc+model("SW_Kailh_Choc_V1")+model("MBK_1U_clearance_seated")))
    pads=rect(-4.5,-1.0,4.5,1.0,"F.CrtYd")+rect(-4.38,-.78,4.38,.78,"F.Fab")
    pads+="".join(pad(str(i+1),(i-2)*1.8,0,.8,1.55) for i in range(5))
    (LIB/"Sprintek_Host_Wires.kicad_mod").write_text(custom("Sprintek_Host_Wires","through_hole",pads))
    (LIB/"M2_Carrier_Mount.kicad_mod").write_text(custom("M2_Carrier_Mount","exclude_from_bom board_only",
        pad("",0,0,2.2)+'(fp_circle (center 0 0) (end 2.7 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.Fab"))'))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("vendor_zip",type=Path);make(p.parse_args().vendor_zip)
