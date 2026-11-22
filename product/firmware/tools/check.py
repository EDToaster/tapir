#!/usr/bin/env python3
"""Validate reference keymap, board geometry, resolved build roles and UF2 records."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--workspace", type=Path, help="inspect fresh west build outputs instead of bundled evidence")
args = ap.parse_args()
ref = (ROOT / "tests/reference/corne.keymap").read_bytes()
assert hashlib.sha256(ref).hexdigest() == "022c26aedbf0ac2c8a550b4c1b0df47176efb867bf4d6e4b0b9fca7bdf22db71"
reference = ref.decode()
actual = (ROOT / "config/tapir.keymap").read_text()

def bindings(text, layer):
    m = re.search(r"\b" + layer + r"\s*\{\s*display-name[^;]+;\s*bindings\s*=\s*<([^>]*)>", text)
    return [" ".join(t.split()) for t in m.group(1).split("&")[1:]]

for layer in ("def", "nav", "num"):
    before, after = bindings(reference, layer), bindings(actual, layer)
    assert len(before) == 42 and after[:42] == before and len(after) == 45, layer
    assert after[42:] == (["mkp LCLK", "mo 3", "mkp RCLK"] if layer == "def" else ["trans"] * 3)
assert bindings(actual, "scroll") == ["trans"] * 45
for old, new in zip(re.findall(r"hold-trigger-key-positions = <([^>]+)", reference),
                    re.findall(r"hold-trigger-key-positions = <([^>]+)", actual), strict=True):
    assert list(map(int, new.split())) == [n for n in map(int, old.split()) if n < 42]
for behavior in ("hml", "hmr"):
    def settings(text):
        body = re.search(behavior + r": " + behavior + r" \{(.*?)\};", text, re.S).group(1)
        return re.sub(r"hold-trigger-key-positions = <[^>]+>;", "", body).split()
    assert settings(reference) == settings(actual)
print("PASS: all 126 original layer bindings, both effective hold-taps and 45-position scroll overlay")

dtsi = (ROOT / "config/boards/shields/tapir/tapir-transform.dtsi").read_text()
coords = [tuple(map(int, pair)) for pair in re.findall(r"RC\((\d+),(\d+)\)", dtsi)]
assert coords == [(r,c) for r in range(3) for c in range(12)] + [(3,c) for c in (3,4,5,6,7,8,0,1,2)]
geometry = json.loads((ROOT.parent / "design/geometry.json").read_text())["halves"]
legends = ["Esc Q W E R T Y U I O P \\", "Shift A S D F G H J K L ; '", "Ctrl Z X C V B N M , . / Enter"]
base_labels = " ".join(legends).split() + ["Alt","Raise","Space","Bksp","Lower","Tab","L","Scroll","R"]
seen = set()
for hand, half in geometry.items():
    for k in half["switches"] + half["buttons"]:
        physical = (k["row"], k["col"] if hand == "left" else 11-k["col"])
        pos = coords.index(physical)
        assert base_labels[pos] == k["label"] and pos not in seen, (hand, k["ref"], pos, k["label"])
        seen.add(pos)
assert seen == set(range(45))
print("PASS: 45 unique physical matrix intersections match all 45 ECAD geometry legends")

for hand in ("left", "right"):
    b = args.workspace / ("build-"+hand) / "zephyr" if args.workspace else ROOT / "build-evidence" / hand
    cfg = (b / (".config" if args.workspace else "resolved.config")).read_text().splitlines()
    dt = (b / "zephyr.dts").read_text()
    for opt in ("ZMK_BLE", "ZMK_SPLIT", "ZMK_SLEEP", "ZMK_PM_DEVICE_SUSPEND_RESUME", "ZMK_STUDIO", "GPIO_HOGS"):
        assert "CONFIG_" + opt + "=y" in cfg, (hand, opt)
    for opt in ("ZMK_SPLIT_ROLE_CENTRAL", "ZMK_USB", "PS2_GPIO", "ZMK_INPUT_MOUSE_PS2", "ZMK_INPUT_LISTENER"):
        assert ("CONFIG_" + opt + "=y" in cfg) == (hand == "right"), (hand, opt)
    assert re.search(r"charge_rate_safe\s*\{[^}]*gpios = < 0xd 0x0 >;[^}]*input;", dt, re.S)
    if hand == "right":
        for prop, port, pin in (("sda",1,15), ("scl",0,15), ("rst",0,19), ("enable",1,1)):
            assert f"{prop}-gpios = < &gpio{port} {pin:#x} 0x0 >;" in dt
    rows = re.search(r"row-gpios = ([^;]+)", dt).group(1)
    cols = re.search(r"col-gpios = ([^;]+)", dt).group(1)
    pads = lambda group: [int(v, 16) for v in re.findall(r"&xiao_d (0x\w+)", group)]
    assert pads(rows) == list(range(4)) and pads(cols) == (list(range(4,10)) if hand == "left" else list(range(9,3,-1)))
    raw = (b / "zmk.uf2").read_bytes()
    assert raw and len(raw) % 512 == 0
    expected, count = 0x27000, len(raw)//512
    for n in range(count):
        block = raw[n*512:(n+1)*512]
        magic0, magic1, flags, addr, size, index, total, family = struct.unpack_from("<8I", block)
        assert (magic0,magic1,struct.unpack_from("<I",block,508)[0]) == (0x0A324655,0x9E5D5157,0x0AB16F30)
        assert (index,total,family) == (n,count,0xADA52840) and flags & 0x2000
        assert addr == expected and 0 < size <= 476 and addr+size <= 0xEC000
        expected += size
    print(f"PASS {hand}: {count} nRF52840 UF2 blocks, 0x27000..{expected:#x} exclusive, correct Kconfig roles and exposed pins")
