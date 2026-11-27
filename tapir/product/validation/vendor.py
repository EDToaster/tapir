"""Extract only selected interface facts, not vendor design files, from the Seeed archive.

python product/validation/vendor.py path/to/Seeed_Studio_XIAO_nRF52840_Plus.zip
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

URL = "https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip"
SHA = "f5e4e0e9c7d1725a89be2677549734f6ad96a8e00a16cb1742e0b3abfa99bdd9"


def extract(file):
    actual = hashlib.sha256(file.read_bytes()).hexdigest()
    if actual != SHA:
        raise ValueError("Wrong archive/revision; no implicit update of charger or GPIO evidence")
    with zipfile.ZipFile(file) as z, tempfile.TemporaryDirectory() as d:
        name, = [n for n in z.namelist() if n.endswith("v1.1.kicad_sch")]
        sch = Path(d) / "xiao.kicad_sch"
        sch.write_bytes(z.read(name))
        xml = Path(d)/"netlist.xml"
        subprocess.run(["kicad-cli","sch","export","netlist","--format","kicadxml","-o",xml,sch],check=True)
        tree = ET.parse(xml)
    nets = {}
    for item in tree.findall("./nets/net"):
        for n in item.findall("node"):
            nets[n.get("ref"),n.get("pin")]=item.get("name")
    vals={c.get("ref"):c.findtext("value") for c in tree.findall("./components/comp")}
    selected = {str(p):nets[("U4",str(p))] for p in range(1,18)}
    assert vals["U2"]=="BQ25100" and [vals[r].lower() for r in ["R18","R12"]]==["2.7k","2.7k"]
    assert nets["U2","B2"]==nets["R12","1"]==nets["R18","1"] and "HICHG" in nets["R12","2"]
    assert "GND" in nets["R18","2"].upper(), nets["R18","2"]
    return {"archive":URL,"sha256":actual,"source_member":name,"method":"KiCad CLI schematic netlist XML export",
            "module_pads":selected,"scope":"Directly numbered U4 pins 1..17. Separate battery/debug contacts are audited in product/electronics/reports/xiao-hidden-lands.json.",
            "charger_marked":vals["U2"],
            "iset":{"default_to_ground_ohm":2700,"gpio_branch_ohm":2700,"gpio":nets["R12","2"],
                    "datasheet":"https://www.ti.com/lit/ds/symlink/bq25100.pdf",
                    "cell_datasheet":"https://cdn-shop.adafruit.com/product-files/1570/1570datasheet.pdf",
                    "ki_min_aohm":129,"ki_max_aohm":145,"assumed_r_tolerance":0.01}}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("--output",type=Path,default=Path(__file__).with_name("vendor-v11.json"))
    a=p.parse_args()
    a.output.write_text(json.dumps(extract(a.archive),indent=2)+"\n")
