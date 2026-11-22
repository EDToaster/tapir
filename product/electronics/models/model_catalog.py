"""Source and audit portable models. Standard library except physical verification.

Examples: python model_catalog.py verify; python model_catalog.py fetch /tmp/ref;
python model_catalog.py compare-regenerated /tmp/new-fit-models.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
KREV = "ca5b7874dad95c1c36b7ad8db6ca6b82e4a2a89e"
KBASE = f"https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/{KREV}/"
SREV = "aefcf65038d48d2666ff14530d482be3c350fa6e"
SBASE = f"https://raw.githubusercontent.com/kiswitch/kiswitch/{SREV}/"
KRIGHTS = "KiCad CC-BY-SA-4.0 + electronic-design exception; licenses/KiCad-LICENSE.md and per-family CREDITS"
TAPIR = "Original Tapir authored B-rep; no vendor B-rep or mesh redistributed"
SEE = "https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip"
HOST = "https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip"
MBK = "https://raw.githubusercontent.com/FKcaps/mbk-3dmodels/6dd2d0c031ba6d02dcdf05325d9b4bebc6369a8f/1u.stl"
JREF = "https://raw.githubusercontent.com/AcheronProject/acheron_3D/4d9d420dfb02e4c7346ce7c05ca6e1c95a868e05/JST-S2B-PH-SM4-TB.STEP"
SPECS = {}


def entry(name, footprint, part, status, source, license, digest):
    SPECS[name+".step"] = dict(
        footprint=footprint, part=part, fidelity=status, source=source,
        reuse=license, sha256=digest, model_rotation_deg=[0,0,0],
        model_offset_mm=[0,0,0], model_scale=[1,1,1],
    )


for n, fam, part, status, h in [
    ("C_0603_1608Metric", "Capacitor_SMD", "C1,C2: 0603/1608", "package only; thickness depends on actual selected capacitor", "4857b3dc717675bf1fb22edda622ac3b3ae03cf44d81eefaf3fa3ba3a86d84c1"),
    ("D_SOD-323", "Diode_SMD", "1N4148WS-7-F", "SOD-323 package CAD, not die-specific", "cd8619b2119cd95683a2c5e660ab4f2d4db674f696cd6f9e9756f221171a214d"),
    ("R_0603_1608Metric", "Resistor_SMD", "R1,R2,R3: 0603/1608", "package only; suffix/value does not follow from body geometry", "1875571c326d0d9e96f36b4efeb8094068ef7619f0a449c781caf0b49c2e5861"),
    ("SOT-23-6", "Package_TO_SOT_SMD", "TPS22918DBVR", "nominal six-terminal SOT-23/DBV package, not a TI assembly model", "c9fe686b4d1b56927a41fa84a9bc1efb61d8a45a123a3db43bcaa05c2891d635"),
    ("SW_SPDT_PCM12", "Button_Switch_SMD", "PCM12SMTR", "KiCad native; original model header explicitly identifies PCM12SMTR", "a10ea113b1599b80249c9f289ca60875d1442ab8e7b62a025b047afe6e77cf92"),
    ("SW_SPST_PTS810", "Button_Switch_SMD", "PTS810SJM250SMTR LFS", "PTS810 J-bend series; 2.50 mm height verified, actuator grade/force not modeled", "03ea59013f361d6becd35559a0a130d1ad29f382cf861d2a1365880acf17005a"),
]:
    entry(n, n, part, status, KBASE+fam+".3dshapes/"+n+".step", KRIGHTS, h)

entry("SW_Kailh_Choc_V1", "Choc_PG1350", "Kailh CPG135001D01 (red)",
      "KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative",
      SBASE+"library/3dmodels/3d-library.3dshapes/SW_Kailh_Choc_V1.stp",
      "keyswitch-kicad-library contributors 2019-2022, retained KiSwitch-MIT.txt; unmodified byte content",
      "669d72c083f226e1f9ee9e9dc8424c18e9641984223ba5422a1235d773a6a9a8")
entry("MBK_1U_clearance_seated", "Choc_PG1350", "FKcaps MBK regular 1u",
      "Independent seated keycap envelope; excludes stem prongs, not mold/print geometry",
      "https://github.com/FKcaps/mbk-3dmodels", TAPIR,
      "f278bcfdb34eb2ef670a3e4da18cb3f1c0cd8e1cc9d90e8212baa20396bcb5df")
entry("XIAO_nRF52840_Plus_nonSense_fit", "XIAO-nRF52840-Plus-SMD", "Seeed 102010672",
      "Independently constructed from non-Sense Plus v1.1 artwork; 23 edge positions, 14 header holes, no IMU/microphone; Z allowances",
      SEE, TAPIR, "473c1f1707f579a3aa9c30ad0d799396a8ecea2b00b3b9e668b62a039397126d")
entry("JST_S2B_PH_SM4_TB_fit", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "S2B-PH-SM4-TB(LF)(SN)",
      "Original simplified JST PH side-entry surface-mount 2-position fit body from drawing; no latch/insertion-force validation",
      "https://www.jst.co.uk/downloads/series/ePH_(24-12-09).pdf", TAPIR,
      "93d7d3b5166d3f01b5f6e3d9c525bd92717e6e0d9fa9f81a815af7a71ebc8cf1")

REFERENCE = {
    "seeed-plus-v11.zip": (SEE,"f5e4e0e9c7d1725a89be2677549734f6ad96a8e00a16cb1742e0b3abfa99bdd9"),
    "seeed-host.zip": (HOST,"671cb119639e489091b87a64e070d4aba1f22860ddfdbecc85ff143c0c295e28"),
    "fk-mbk-1u-render-only.stl": (MBK,"f06627a7bda821dc55e585d3d3b5440c10043b0a37e4bee5272678c83048ca87"),
    "jst-third-party-private-review.step": (JREF,"67493412dbd25960c100685f6bc193c6bb7a29cac04f6e8e5e8221894478aee1"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def geometry_prefix(data):
    # On OCCT 8.0.1.1: all B-reps, placements, product names and assembly
    # definitions occur before the first presentation block. OCCT may reorder
    # colored presentation entities. Never use this instead of the shipped hash.
    match = re.search(rb"^#\d+ = MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION", data, re.M)
    if not match:
        raise ValueError("no AP214 presentation section")
    return sha(data[:match.start()])


def check_bindings():
    lib = ROOT.parent / "Tapir.pretty"
    expected = {}
    for n, spec in SPECS.items():
        expected.setdefault(spec["footprint"], set()).add(n)
    for mod in sorted(lib.glob("*.kicad_mod")):
        data = mod.read_text()
        files = re.findall(r'\(model\s+"([^"]+)"', data)
        required = expected.get(mod.stem, set())
        actual = {f"${{KIPRJMOD}}/../models/{name}" for name in required}
        if len(files) != len(actual) or set(files) != actual:
            raise ValueError(f"{mod.name}: expected {actual} but found {files}")
        # This project's footprint generators put models last; hidden text
        # properties earlier in the footprint are unrelated to hidden models.
        model_block = data.partition("(model ")[2]
        if files and ("(hide yes)" in model_block or len(re.findall(r"\(rotate\s*\(xyz 0 0 0\)",model_block))!=len(files)
                      or len(re.findall(r"\(offset\s*\(xyz 0 0 0\)",model_block))!=len(files)
                      or len(re.findall(r"\(scale\s*\(xyz 1 1 1\)",model_block))!=len(files)):
            raise ValueError(f"unexpected hidden model or nonidentity transform in {mod.name}")
    if expected.keys() - {p.stem for p in lib.glob("*.kicad_mod")}:
        raise ValueError("missing registered footprint")


def measure(path):
    from build123d import import_step
    shape = import_step(path)
    solids = shape.solids()
    if not shape.is_valid or not solids or not all(s.volume > 0 for s in solids):
        raise ValueError(f"failed OCCT validity: {path.name}")
    bb = shape.bounding_box()
    clean = lambda coord: [round(v,4)+0.0 for v in coord]
    measured = dict(solids=len(solids), bbox_min_mm=clean(bb.min), bbox_max_mm=clean(bb.max),
                    solid_volume_sum_mm3=round(sum(s.volume for s in solids),4))
    if path.name=="SW_Kailh_Choc_V1.step":
        # The final two thin, low-volume solids are the conductive leads. At
        # rest their X/Y centers should enter corresponding PCB holes.
        tails=[s for s in solids if s.volume < 3 and s.bounding_box().min.Z < -2.9]
        centers=sorted([clean(s.bounding_box().center())[:2] for s in tails])
        if len(centers)!=2 or any(abs(v-e)>0.13 for p,q in zip(centers,[[0,5.9],[5,3.8]]) for v,e in zip(p,q)):
            raise ValueError(f"Choc lead centers do not register to Tapir holes: {centers}")
        measured["metal_lead_bbox_centers_xy_mm"]=centers
    return measured


def snapshot():
    result = {}
    for name, spec in sorted(SPECS.items()):
        data=(ROOT/name).read_bytes()
        if sha(data)!=spec["sha256"]:
            raise ValueError(f"shipped SHA-256 mismatch: {name}")
        item=dict(**spec, **measure(ROOT/name))
        if spec["reuse"]==TAPIR:
            item["geometry_prefix_sha256"]=geometry_prefix(data)
        result[name]=item
    return result


def fetch(out, urls):
    out.mkdir(parents=True, exist_ok=True)
    for name,(url,digest) in urls.items():
        with urlopen(url, timeout=45) as r:
            data = r.read()
        if sha(data)!=digest:
            raise ValueError(f"refusing upstream drift at {url}")
        (out/name).write_bytes(data)
        print(name, digest)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="cmd",required=True)
    for cmd in ("verify","emit-manifest","fetch","private-reference","compare-regenerated"):
        sp=sub.add_parser(cmd)
        if cmd in ("fetch","private-reference","compare-regenerated"):
            sp.add_argument("directory",type=Path)
        if cmd=="private-reference":
            sp.add_argument("name",choices=REFERENCE,help="only use within upstream terms; do not redistribute")
    a=p.parse_args()
    if a.cmd in ("verify","emit-manifest"):
        check_bindings()
        measured=snapshot()
        path=ROOT/"manifest.json"
        if a.cmd=="emit-manifest":
            path.write_text(json.dumps(measured,indent=2,sort_keys=True)+"\n")
        elif measured!=json.loads(path.read_text()):
            raise ValueError("manifest mismatch")
        print(f"{len(measured)} valid STEP files; identities, geometry and native footprint bindings verified")
    elif a.cmd=="compare-regenerated":
        manifest=json.loads((ROOT/"manifest.json").read_text())
        for name,spec in manifest.items():
            if "geometry_prefix_sha256" not in spec:
                continue
            path=a.directory/name
            if geometry_prefix(path.read_bytes())!=spec["geometry_prefix_sha256"]:
                raise ValueError(f"geometry changed: {name}")
            if any(spec[k]!=v for k,v in measure(path).items()):
                raise ValueError(f"OCCT measurement changed: {name}")
            print("verified regenerated B-rep", name)
    elif a.cmd=="fetch":
        fetch(a.directory, {n:(s["source"],s["sha256"]) for n,s in SPECS.items() if s["reuse"]!=TAPIR})
    elif a.cmd=="private-reference":
        if a.directory.resolve().is_relative_to(ROOT.parent.parent.parent):
            raise ValueError("store restricted/private-review inputs outside the repository")
        fetch(a.directory, {a.name:REFERENCE[a.name]})
