#!/usr/bin/env python3
"""Compare KiCad's own netlist export of the schematic with the design manifest, pin by pin."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from design import circuit

want, declared = {}, set()
pin_errors = []
checked = 0
reference = json.loads(Path(__file__).with_name("datasheet-pins.json").read_text())
seen = set()
for c in circuit()["components"]:
    if c["mpn"] in reference:
        seen.add(c["mpn"])
        expected = dict(entry.split(":") for entry in reference[c["mpn"]]["pins"].split())
        names = {p: d["name"] for p, d in c["pins"].items()}
        if names != expected:
            pin_errors.append((c["ref"], expected, names))
        checked += len(expected)
    for pad, pin in c["pins"].items():
        declared.add((c["ref"], pad))
        if pin["net"]:
            want[(c["ref"], pad)] = pin["net"]
got = {}
for net in ET.parse(sys.argv[1]).getroot().iter("net"):
    name = net.get("name").lstrip("/")
    for node in net.iter("node"):
        if not name.startswith("unconnected-"):
            got[(node.get("ref"), node.get("pin"))] = name
bad = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
critical = json.loads(Path(__file__).with_name("critical-connections.json").read_text())["nets"]
critical_errors = []
for ref, pins in critical.items():
    for pin, expected in pins.items():
        k = (ref, pin)
        if k not in declared or want.get(k) != expected or got.get(k) != expected:
            critical_errors.append(k)
            print(f"CRITICAL CONNECTION {ref}.{pin}: expected {expected!r}, "
                  f"manifest {want.get(k)!r}, schematic {got.get(k)!r}")
for k in bad:
    print("MISMATCH", k, "manifest", want.get(k), "schematic", got.get(k))
for part, expected, actual in pin_errors:
    print("DATASHEET MISMATCH", part, "reference", expected, "manifest", actual)
if unused := reference.keys() - seen:
    print("DATASHEET FIXTURES WITHOUT A MANIFEST MATCH", sorted(unused))
print(f"schematic netlist: {len(got)} connected pins, {len(set(got.values()))} nets, {len(bad)} mismatches; "
      f"datasheet: {checked} manifest pins checked, {len(pin_errors)} parts mismatch")
print(f"critical connections: {sum(map(len, critical.values()))} independent pin assertions, "
      f"{len(critical_errors)} mismatches")
sys.exit(1 if bad or pin_errors or unused or critical_errors else 0)
