"""Write bom.csv: every part on the coupon, plus the hand-fitted items that are not in the schematic."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKER = {"TMR2617S": "MultiDimension (MDT)", "CD74HC": "Texas Instruments", "AO3401A": "Alpha & Omega",
         "CC0603": "YAGEO", "0603B": "Fenghua (FH)", "CL10": "Samsung Electro-Mechanics", "0603WAF": "UNI-ROYAL",
         "S2B-PH": "JST", "PCM12SMTR": "C&K", "KT-0603R": "Hubei KENTO"}
HAND = [
    # refs, qty, value, part number, maker, listing, note
    ("A1", 1, "nRF52840 Pro Micro-format controller", "nice!nano v2 or pin-compatible clone", "owner supplied", "",
     "Hand-solder on the top side, chip side up, USB at the board edge. Sockets are fine."),
    ("SW1-SW6", 6, "Low-profile magnetic switch", "Gateron Low Profile Magnetic Jade Pro (KS-33D)", "Gateron",
     "https://nuphy.com/products/gateron-low-profile-magnetic-jade-pro-switches",
     "Sold in packs of 70 or 90. Press-fit into the board holes; nothing is soldered."),
    ("", 6, "Keycap", "Low-profile MX-stem keycap, 1u", "any", "", "Optional for the measurements."),
    ("BT1", 1, "1-cell LiPo with JST-PH plug", "Adafruit 1578 (3.7 V 500 mAh)", "Adafruit",
     "https://www.adafruit.com/product/1578", "Optional. Check plug polarity against the board silk with a meter first."),
    ("H1-H4", 4, "M2 standoff, 8 mm or taller, with screws", "", "any", "", "Use brass or nylon near the magnets."),
    ("J3", 1, "1x10 pin header, 2.54 mm", "", "any", "", "Optional, for a logic analyser or scope."),
]


def num(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return m.group(1), int(m.group(2))


def main():
    parts = json.loads((ROOT / "build" / "design.json").read_text())["components"]
    groups = {}
    for c in parts:
        if c["fit"] != "jlc":
            continue
        key = (c["value"], c["mpn"], c["lcsc"], c["jlc_class"], c["description"],
               c["footprint"].split(":")[1], "Not fitted (DNP)" if c["dnp"] else "JLCPCB assembly")
        groups.setdefault(key, []).append(c["ref"])
    rows = []
    for (value, mpn, lcsc, klass, desc, fp, fit), refs in groups.items():
        refs.sort(key=num)
        maker = next((m for p, m in MAKER.items() if mpn.startswith(p)), "")
        link = f"https://www.lcsc.com/product-detail/{lcsc}.html" if lcsc and fit.startswith("JLC") else ""
        rows.append([",".join(refs), len(refs), value, mpn if fit.startswith("JLC") else "", maker if fit.startswith("JLC") else "",
                     fp, lcsc if fit.startswith("JLC") else "", klass if fit.startswith("JLC") else "", fit, desc, link])
    rows.sort(key=lambda r: (r[8] != "JLCPCB assembly", num(r[0].split(",")[0])))
    for refs, qty, value, mpn, maker, link, note in HAND:
        rows.append([refs, qty, value, mpn, maker, "", "", "", "Hand-fitted", note, link])
    with (ROOT / "bom.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Refs", "Qty", "Value", "Part number", "Manufacturer", "Footprint", "LCSC", "JLC class", "Fit", "Notes", "Listing"])
        w.writerows(rows)
    fitted = sum(r[1] for r in rows if r[8] == "JLCPCB assembly")
    print(f"bom.csv: {len(rows)} lines, {fitted} parts assembled by JLCPCB")


if __name__ == "__main__":
    main()
