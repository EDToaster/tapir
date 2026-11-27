#!/usr/bin/env python3
"""Compare KiCad's own netlist export of the schematic with the design manifest, pin by pin."""
import sys
import xml.etree.ElementTree as ET
from design import circuit

want = {}
for c in circuit()["components"]:
    for pad, pin in c["pins"].items():
        if pin["net"]:
            want[(c["ref"], pad)] = pin["net"]
got = {}
for net in ET.parse(sys.argv[1]).getroot().iter("net"):
    name = net.get("name").lstrip("/")
    for node in net.iter("node"):
        if not name.startswith("unconnected-"):
            got[(node.get("ref"), node.get("pin"))] = name
bad = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
for k in bad:
    print("MISMATCH", k, "manifest", want.get(k), "schematic", got.get(k))
print(f"schematic netlist: {len(got)} connected pins, {len(set(got.values()))} nets, {len(bad)} mismatches")
sys.exit(1 if bad else 0)
