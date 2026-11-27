"""TMR half test coupon: component and net manifest.

This file is the single source for the schematic, the board netlist, the BOM
and the pin map. Pin numbers are PCB pad numbers. Physical placement lives in
place_board.py. Evidence for each part is in ../README.md and ../../design-decisions.md.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = "tmr-coupon"
LIB = "TmrHalf"
REV = "A"


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "tmr-half-coupon/" + name))


# Rail A (keys 1-3) carries the datasheet 100 nF bypass capacitors.
# Rail B (keys 4-6) carries 10 nF, to compare noise and pulsed-power rise time.
KEYS = [dict(n=n, col=(n - 1) % 3, row=(n - 1) // 3, rail="AB"[(n - 1) // 3]) for n in range(1, 7)]

# nice!nano v2 header, viewed from the top with the USB connector at the top
# edge and the module's components facing up. Pads 1-12 run down the left
# column, pads 13-24 run UP the right column (DIP order), so pad 24 is
# top-right. Source: nice!nano v2 pinout drawing (nicekeyboards.com).
CONTROLLER = {
    1: ("P0.06", None), 2: ("P0.08", None), 3: ("GND", "GND"), 4: ("GND", "GND"),
    5: ("P0.17", "S0"), 6: ("P0.20", "S1"), 7: ("P0.22", "S2"), 8: ("P0.24", "S3"),
    9: ("P1.00", "MUX_EN_N"), 10: ("P0.11", "PWR_A_N"), 11: ("P1.04", "PWR_B_N"), 12: ("P1.06", None),
    13: ("P0.09", None), 14: ("P0.10", None), 15: ("P1.11", None), 16: ("P1.13", None),
    17: ("P1.15", None), 18: ("P0.02/AIN0", "AIN_A"), 19: ("P0.29/AIN5", "AIN_B"),
    20: ("P0.31/AIN7", "AIN_SPARE"), 21: ("VCC", "VCC"), 22: ("RST", "RST"), 23: ("GND", "GND"),
    24: ("B+", "BAT_SW"),
}

# Debug header J3, pin 1 first.
DEBUG = ["GND", "VCC", "VSW_A", "VS_A", "VSW_B", "VS_B", "MUXA", "MUXB", "S0", "AIN_SPARE"]

R0603, C0603 = "R_0603_1608Metric", "C_0603_1608Metric"
PARTS = {
    # value: (manufacturer part number, LCSC/JLCPCB code, JLC library class, description)
    "TMR2617S-AAC-0.500-500": ("TMR2617S-AAC-0.500-500", "C55130211", "Extended", "MDT linear TMR sensor, SOT-23-3"),
    "CD74HC4067SM96": ("CD74HC4067SM96", "C98457", "Extended", "TI 16:1 analog multiplexer, SSOP-24"),
    "AO3401A": ("AO3401A", "C15127", "Basic", "P-channel MOSFET, SOT-23"),
    "100nF": ("CC0603KRX7R9BB104", "C14663", "Basic", "100 nF 50 V X7R 0603"),
    "10nF": ("0603B103K500NT", "C57112", "Basic", "10 nF 50 V X7R 0603"),
    "100pF": ("CL10C101JB8NNNC", "C14858", "Basic", "100 pF 50 V C0G 0603"),
    "1uF": ("CL10A105KB8NNNC", "C15849", "Basic", "1 uF 50 V X5R 0603"),
    "0R": ("0603WAF0000T5E", "C21189", "Basic", "0 ohm 0603"),
    "10R": ("0603WAF100JT5E", "C22859", "Basic", "10 ohm 1% 0603"),
    "100R": ("0603WAF1000T5E", "C22775", "Basic", "100 ohm 1% 0603"),
    "10k": ("0603WAF1002T5E", "C25804", "Basic", "10 kohm 1% 0603"),
    "100k": ("0603WAF1003T5E", "C25803", "Basic", "100 kohm 1% 0603"),
    "S2B-PH-SM4-TB": ("S2B-PH-SM4-TB(LF)(SN)", "C295747", "Extended", "JST PH 2-pin side-entry battery connector"),
    "MSK12C02": ("MSK12C02", "C431540", "Extended", "SHOU HAN SPDT slide switch, side actuated"),
}


def circuit():
    out = []

    def add(ref, value, fp, pins, *, dnp=False, fit="jlc", note=""):
        mpn, lcsc, klass, desc = PARTS.get(value, ("", "", "", ""))
        out.append(dict(
            ref=ref, value=value, footprint=f"{LIB}:{fp}", uuid=uid(ref), dnp=dnp, fit=fit,
            mpn=mpn, lcsc=lcsc, jlc_class=klass, description=desc or note,
            pins={str(n): dict(name=name, net=net, type=t) for n, (name, net, t) in pins.items()}))

    def two(ref, value, a, b, **kw):
        fp = R0603 if ref.startswith("R") else C0603
        add(ref, value, fp, {1: ("1", a, "passive"), 2: ("2", b, "passive")}, **kw)

    # Controller module. Hand-fitted on the top side; nothing here is assembled by the fab.
    types = {"VCC": "power_out"}
    add("A1", "nice!nano v2 (clone)", "ProMicro_nRF52840_THT",
        {n: (name, net, types.get(name, "passive" if name in ("GND", "B+", "RST") else "bidirectional"))
         for n, (name, net) in CONTROLLER.items()},
        fit="hand", note="nRF52840 Pro Micro-format controller, owner supplied")

    # One sensor cell per key.
    for k in KEYS:
        n, rail = k["n"], "VS_" + k["rail"]
        add(f"U{n}", "TMR2617S-AAC-0.500-500", "SOT-23-3_TMR2617S",
            {1: ("VCC", rail, "power_in"), 2: ("VOUT", f"OUT{n}", "output"), 3: ("GND", "GND", "power_in")})
        two(f"C{n}", "100nF" if k["rail"] == "A" else "10nF", rail, "GND")
        # Datasheet CL. Fitted on the middle key of each row only.
        two(f"C{10 + n}", "100pF", f"OUT{n}", "GND", dnp=k["col"] != 1)

    # One 16:1 multiplexer per rail. Channels 0-2 are keys, channel 4 reads the
    # rail through a divider, every other channel is tied to ground.
    order = {1: "COM", **{p: f"I{9 - p}" for p in range(2, 10)}, 10: "S0", 11: "S1", 12: "GND",
             13: "S3", 14: "S2", 15: "E_N", **{p: f"I{31 - p}" for p in range(16, 24)}, 24: "VCC"}
    for ref, rail, keys in (("U7", "A", (1, 2, 3)), ("U8", "B", (4, 5, 6))):
        nets = {"COM": "MUX" + rail, "GND": "GND", "VCC": "VCC", "E_N": "MUX_EN_N",
                **{f"S{i}": f"S{i}" for i in range(4)}, **{f"I{i}": "GND" for i in range(16)},
                **{f"I{i}": f"OUT{key}" for i, key in enumerate(keys)}, "I4": "MON_" + rail}
        kinds = {"VCC": "power_in", "GND": "power_in"}
        add(ref, "CD74HC4067SM96", "SSOP-24_5.3x8.2mm_P0.65mm",
            {p: (name, nets[name], kinds.get(name, "passive")) for p, name in order.items()})

    # Sensor rail switches. The gate pull-down keeps each rail ON until firmware drives the pin high.
    for i, rail in enumerate("AB", 1):
        add(f"Q{i}", "AO3401A", "SOT-23",
            {1: ("G", "GATE_" + rail, "passive"), 2: ("S", "VCC", "passive"), 3: ("D", "VSW_" + rail, "passive")})
        two(f"R{i}", "100R", f"PWR_{rail}_N", "GATE_" + rail)
        two(f"R{i + 2}", "100k", "GATE_" + rail, "GND")
        two(f"R{i + 4}", "10R", "VSW_" + rail, "VS_" + rail)      # current-sense shunt
        two(f"R{i + 6}", "10k", "VS_" + rail, "MON_" + rail)      # rail monitor, upper
        two(f"R{i + 8}", "10k", "MON_" + rail, "GND")             # rail monitor, lower
        two(f"C{i + 16}", "100pF", "MON_" + rail, "GND")              # small, so the monitor follows the rail edge
        two(f"R{i + 10}", "0R", "MUX" + rail, "AIN_" + rail)      # ADC series position
        two(f"C{i + 18}", "1nF", "AIN_" + rail, "GND", dnp=True, note="Optional ADC input capacitor, not fitted")
        two(f"C{i + 6}", "100nF", "VCC", "GND")                    # mux supply bypass
    two("R13", "10k", "MUX_EN_N", "GND")
    two("C9", "1uF", "VCC", "GND")

    # Optional battery path: connector -> slide switch -> controller B+.
    add("J1", "S2B-PH-SM4-TB", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
        {1: ("BAT+", "BAT_P", "passive"), 2: ("BAT-", "GND", "passive"), "MP": ("MP", "GND", "passive")})
    add("S1", "MSK12C02", "SW_SPDT_Shouhan_MSK12C02",
        {1: ("ON", "BAT_SW", "passive"), 2: ("COM", "BAT_P", "passive"), 3: ("OFF", None, "passive"),
         "SH": ("SHELL", "GND", "passive")})
    add("J2", "RESET pads", "PinHeader_1x02_P2.54mm",
        {1: ("RST", "RST", "passive"), 2: ("GND", "GND", "passive")}, fit="none",
        note="Short these two pads to reset; double-tap for the bootloader")
    add("J3", "Debug header", "PinHeader_1x10_P2.54mm",
        {i: (net, net, "passive") for i, net in enumerate(DEBUG, 1)}, fit="none",
        note="Optional 2.54 mm header or probe points")
    return {"title": f"TMR half test coupon, rev {REV}", "components": out}


def mechanical():
    """Board-only items with no schematic symbol."""
    return ([dict(ref=f"SW{k['n']}", value="Gateron KS-33D LP magnetic", footprint="SW_Gateron_LP_Magnetic_KS-33D")
             for k in KEYS]
            + [dict(ref=f"H{i}", value="M2", footprint="MountingHole_M2_NPTH") for i in range(1, 5)])


if __name__ == "__main__":
    (ROOT / "build").mkdir(exist_ok=True)
    data = circuit()
    (ROOT / "build" / "design.json").write_text(json.dumps(data, indent=2) + "\n")
    nets = sorted({p["net"] for c in data["components"] for p in c["pins"].values() if p["net"]})
    print(len(data["components"]), "components,", len(nets), "nets")
