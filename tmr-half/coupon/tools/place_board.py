#!/usr/bin/python3
"""Place the coupon. Writes the unrouted board to build/; never touches the routed board.

Coordinates are millimetres from the board's top-left corner, viewed from the
top (switch) side, +Y toward the edge nearest the user. KiCad coordinates are
these plus ORIGIN. Every surface-mount part is on the bottom so one-sided
assembly covers the whole board; the controller and switches go on top.
"""
import math
import pcbnew as k
from design import ROOT, STEM, LIB, REV, KEYS, CONTROLLER, DEBUG, circuit, mechanical, uid
from project import create
import silk_pattern

ORIGIN = (100.0, 100.0)
W, H, RADIUS = 92.0, 50.0, 2.0
KEY_X, KEY_Y = (13.5, 32.55, 51.6), (14.0, 33.05)     # 19.05 mm pitch
SENSOR_DY, CAP_DX = 4.40, 2.95                        # sensor centre south of the switch centre
A1 = (74.62, 17.97)                                   # centre of the controller pad field
HOLES = ((3, 3), (89, 3), (3, 47), (89, 47))
FIDUCIALS = ((3, 13), (90, 14), (57, 46))
ANTENNA = ((63.5, 30.45), (86.0, 30.45), (86.0, 35.6), (63.5, 35.6))
N, S, E, Wd = (0, -1), (0, 1), (1, 0), (-1, 0)


def key_xy(n):
    k_ = KEYS[n - 1]
    return KEY_X[k_["col"]], KEY_Y[k_["row"]]


def plan():
    """ref -> (x, y, pad, direction): rotate until that pad lies in that direction from the part centre."""
    p = {}
    for k_ in KEYS:
        n = k_["n"]; x, y = key_xy(n)
        p[f"U{n}"] = (x, y + SENSOR_DY, "3", S)
        p[f"C{n}"] = (x - CAP_DX, y + SENSOR_DY, "1", N)
        p[f"C{10 + n}"] = (x + CAP_DX, y + SENSOR_DY, "1", N)
    for i, (x, y) in enumerate(((33.5, 6.6), (37.5, 25.5)), 1):
        monitor_x = x + (8.0 if i == 1 else 6.1)
        p[f"U{6+i}"] = (x, y, "1", (1, 1))
        p[f"C{6+i}"] = (x + 6.1, y - 3.5, "1", Wd)
        p[f"R{6+i}"] = (monitor_x, y + 3.8, "1", E)
        p[f"R{8+i}"] = (monitor_x, y + 5.55, "1", Wd)
        p[f"C{16+i}"] = (monitor_x, y + 7.3, "1", Wd)
    p.update({
        "C9": (78.6, 11.62, "1", E), "C20": (78.6, 14.95, "1", E), "R12": (78.6, 16.7, "1", Wd),
        "R11": (78.6, 19.24, "1", Wd), "C19": (78.6, 20.99, "1", E), "R13": (70.3, 20.4, "1", Wd),
        "R3": (70.3, 22.3, "1", E), "R1": (70.3, 24.05, "1", Wd), "Q1": (74.0, 23.1, "3", E), "R5": (77.6, 23.1, "1", Wd),
        "R4": (70.3, 26.9, "1", E), "R2": (70.3, 28.65, "1", Wd), "Q2": (74.0, 27.7, "3", E), "R6": (77.6, 27.7, "1", Wd),
        "J1": (77.0, 44.6, "1", N), "S1": (67.5, 48.2, "2", N),
        "Q3": (81.25, 37.8, "3", S), "R14": (76.1, 37.0, "1", E),
        "D1": (83.65, 44.1, "2", N), "R15": (83.65, 41.8, "1", Wd),
    })
    return p


TOP = {"A1": (*A1, "1", (-1, -1)), "J2": (85.5, 40.0, "2", E), "J3": (60.65, 5.0, "2", S)}


def xy(x, y):
    return k.VECTOR2I(k.FromMM(ORIGIN[0] + x), k.FromMM(ORIGIN[1] + y))


def mm(v):
    return k.FromMM(v)


def edge(b, a, c, tag, mid=None):
    s = k.PCB_SHAPE(b)
    if mid:
        s.SetShape(k.SHAPE_T_ARC); s.SetArcGeometry(xy(*a), xy(*mid), xy(*c))
    else:
        s.SetShape(k.SHAPE_T_SEGMENT); s.SetStart(xy(*a)); s.SetEnd(xy(*c))
    s.SetLayer(k.Edge_Cuts); s.SetWidth(mm(0.05)); s.SetUuid(k.KIID(uid("edge/" + tag))); b.Add(s)


def outline(b):
    r, q = RADIUS, RADIUS * (1 - math.sqrt(0.5))
    edge(b, (r, 0), (W - r, 0), "n"); edge(b, (W, r), (W, H - r), "e")
    edge(b, (W - r, H), (r, H), "s"); edge(b, (0, H - r), (0, r), "w")
    edge(b, (W - r, 0), (W, r), "ne", (W - q, q)); edge(b, (W, H - r), (W - r, H), "se", (W - q, H - q))
    edge(b, (r, H), (0, H - r), "sw", (q, H - q)); edge(b, (0, r), (r, 0), "nw", (q, q))


def label(b, text, x, y, layer, size=0.8, angle=0, justify=None):
    s = k.PCB_TEXT(b); s.SetText(text); s.SetPosition(xy(x, y)); s.SetLayer(layer)
    size = max(size, 1.0)       # JLCPCB asks for silkscreen text at least 1.0 mm high, 0.15 mm stroke
    s.SetTextSize(k.VECTOR2I(mm(size), mm(size))); s.SetTextThickness(mm(max(0.15, size * 0.15)))
    s.SetTextAngle(k.EDA_ANGLE(angle, k.DEGREES_T)); s.SetMirrored(layer == k.B_SilkS)
    if justify is not None:
        s.SetHorizJustify(justify)
    s.SetUuid(k.KIID(uid(f"text/{text}/{x}/{y}/{layer}"))); b.Add(s)


def keepout(b, name, polygon):
    z = k.ZONE(b); b.Add(z); z.SetIsRuleArea(True); z.SetZoneName(name); z.SetLayerSet(k.LSET.ExternalCuMask())
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowFootprints(False)
    loop = z.Outline(); loop.NewOutline()
    for x, y in polygon:
        loop.Append(xy(x, y))
    z.SetUuid(k.KIID(uid("zone/" + name)))


def build():
    assert k.GetBuildVersion().startswith("10."), "Use KiCad 10's Python"
    out = ROOT / "build"; create(out, "..")
    intent = {c["ref"]: c for c in circuit()["components"]}
    b = k.BOARD(); b.SetCopperLayerCount(2); b.GetDesignSettings().SetBoardThickness(mm(1.60))
    b.SetFileName(str(out / (STEM + ".kicad_pcb"))); nets = {}
    outline(b)

    def fp(ref, x, y, pad=None, toward=None, back=False, mech=None):
        c = intent.get(ref, {}); name = mech or c["footprint"].split(":", 1)[1]
        f = k.FootprintLoad(str(ROOT / f"{LIB}.pretty"), name)
        if not f:
            raise ValueError("Unreadable footprint " + name)
        f.SetFPIDAsString(f"{LIB}:{name}"); f.SetReference(ref); f.SetValue(c.get("value", name))
        f.SetUuid(k.KIID(uid("pcb/" + ref)))
        if mech:
            f.SetAttributes(f.GetAttributes() | k.FP_BOARD_ONLY | k.FP_EXCLUDE_FROM_BOM | k.FP_EXCLUDE_FROM_POS_FILES)
        else:
            f.SetPath(k.KIID_PATH("/" + c["uuid"])); f.SetSheetfile(STEM + ".kicad_sch"); f.SetSheetname("/")
            for key, field in (("description", "Description"), ("mpn", "MPN"), ("lcsc", "LCSC")):
                if c[key]:
                    f.SetField(field, c[key]); f.GetField(field).SetVisible(False)
            if c["dnp"]:
                f.SetDNP(True)
            if c["fit"] != "jlc":
                f.SetAttributes(f.GetAttributes() | k.FP_EXCLUDE_FROM_POS_FILES)
        b.Add(f)
        if back:
            f.Flip(k.VECTOR2I(0, 0), k.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetPosition(xy(x, y)); f.Reference().SetVisible(False); f.Value().SetVisible(False)
        for item in f.GraphicalItems():
            if item.GetLayer() in (k.F_SilkS, k.B_SilkS) and item.GetClass() == "PCB_SHAPE":
                item.SetWidth(max(mm(0.15), item.GetWidth()))
        if pad:
            best = None
            for angle in (0, 90, 180, 270):
                f.SetOrientationDegrees(angle)
                q = next(p for p in f.Pads() if p.GetNumber() == pad).GetPosition() - f.GetPosition()
                score = (q.x * toward[0] + q.y * toward[1]) / math.hypot(*toward)
                if best is None or score > best[0] + 1:
                    best = (score, angle)
            f.SetOrientationDegrees(best[1])
        if not mech:
            lost = set(c["pins"]) - {p.GetNumber() for p in f.Pads()}
            assert not lost, f"{ref}: manifest pins {lost} have no pad on {name}"
        # Stable ids for everything inside the footprint, so a rebuild gives an identical file.
        for i, item in enumerate(list(f.GetFields()) + list(f.GraphicalItems()) + list(f.Zones())):
            item.SetUuid(k.KIID(uid(f"pcb/{ref}/item/{i}")))
        for i, p in enumerate(f.Pads()):
            p.SetUuid(k.KIID(uid(f"pcb/{ref}/pad/{i}")))
            n = p.GetNumber()
            if not n or mech:
                continue
            pin = c["pins"][n]; p.SetPinFunction(pin["name"]); p.SetPinType(pin["type"])
            net = pin["net"] or f"unconnected-({ref}-{pin['name']}-Pad{n})"
            if net not in nets:
                nets[net] = k.NETINFO_ITEM(b, net); b.Add(nets[net])
            p.SetNet(nets[net])
        return f

    placed = {}
    for ref, (x, y, pad, toward) in plan().items():
        placed[ref] = fp(ref, x, y, pad, toward, back=True)
    for ref, (x, y, pad, toward) in TOP.items():
        placed[ref] = fp(ref, x, y, pad, toward)
    missing = set(intent) - set(placed)
    if missing:
        raise ValueError(f"unplaced: {sorted(missing)}")
    holes, fiducials = iter(HOLES), iter(FIDUCIALS)
    for m in mechanical():
        ref = m["ref"]
        if ref.startswith("SW"):
            x, y = key_xy(int(ref[2:]))
        else:
            x, y = next(fiducials if ref.startswith("FID") else holes)
        fp(ref, x, y, mech=m["footprint"], back=ref.startswith("FID"))

    # Geometry that the rest of the project relies on. Fail here instead of at the fab.
    def at(ref, pad):
        q = next(p for p in placed[ref].Pads() if p.GetNumber() == pad).GetPosition()
        return round(k.ToMM(q.x) - ORIGIN[0], 4), round(k.ToMM(q.y) - ORIGIN[1], 4)
    for k_ in KEYS:
        n = k_["n"]; x, y = key_xy(n)
        want = {"1": (x - 0.95, y + 3.35), "2": (x + 0.95, y + 3.35), "3": (x, y + 5.625)}
        for pad, (wx, wy) in want.items():
            px, py = at(f"U{n}", pad)
            assert abs(px - wx) < 1e-3 and abs(py - wy) < 1e-3, (n, pad, px, py, wx, wy)
        assert placed[f"U{n}"].GetLayer() == k.B_Cu
    left = [at("A1", str(i)) for i in range(1, 13)]; right = [at("A1", str(i)) for i in range(24, 12, -1)]
    assert left[0] == (67.0, 4.0) and right[0] == (82.24, 4.0), (left[0], right[0])
    assert all(abs(b_[1] - a_[1] - 2.54) < 1e-3 for col in (left, right) for a_, b_ in zip(col, col[1:]))

    keepout(b, "Module antenna end: no tracks, vias or fill", ANTENNA)
    for i, (x, y) in enumerate(HOLES, 1):
        r = 2.55 / math.cos(math.pi / 32)
        keepout(b, f"M2 hardware {i}", [(x + r * math.cos(j * math.tau / 32),
                                         y + r * math.sin(j * math.tau / 32)) for j in range(32)])

    # Top silkscreen.
    F, B = k.F_SilkS, k.B_SilkS
    left_j, right_j = k.GR_TEXT_H_ALIGN_LEFT, k.GR_TEXT_H_ALIGN_RIGHT
    short = lambda name: name.split("/")[0].replace("P", "").replace(".", "") if name.startswith("P") else name
    for i in range(12):
        y = 4.0 + 2.54 * i
        label(b, short(CONTROLLER[i + 1][0]), 65.7, y, F, 0.8, justify=right_j)
        label(b, short(CONTROLLER[24 - i][0]), 83.7, y, F, 1.0, justify=left_j)
    label(b, "USB", A1[0], 1.3, F, 0.9)
    label(b, "CHIP SIDE UP", A1[0], 36.9, F, 1.0)
    label(b, "RESET", 86.77, 37.8, F, 1.0)
    for k_ in KEYS:
        n = k_["n"]; x, y = key_xy(n)
        label(b, f"K{n}", x - 5.5, y - 8.0, F, 0.9)
        label(b, "LED", x, y - 8.0, F)
        label(b, f"K{n}", x - 5.6, y + SENSOR_DY, B, 1.0)
    names = {"VCC": "3V3", "VSW_A": "SWA", "VS_A": "VSA", "VSW_B": "SWB", "VS_B": "VSB", "MUXA": "MXA",
             "MUXB": "MXB", "AIN_SPARE": "A7"}
    for i, net in enumerate(DEBUG):
        label(b, names.get(net, net), 63.0, 5.0 + 2.54 * i, B, 0.75)
    label(b, f"TMR HALF COUPON  REV {REV}", 47.5, 44.6, F, 1.0)
    label(b, "github.com/EDToaster/tapir", 47.5, 46.7, F, 1.0)
    # J1 pad 1 (battery +) is at x = 78, pad 2 (battery -) at x = 76; S1 pin 1 (ON throw) is at x = 69.75.
    for layer in (F, B):
        label(b, "+", 78.0, 38.85, layer, 1.2); label(b, "-", 76.0, 38.85, layer, 1.2)
        label(b, "ON", 69.75, 44.7, layer, 0.8); label(b, "OFF", 65.25, 44.7, layer, 0.8)
    label(b, "BATTERY", 70.9, 38.9, F, 1.0)
    label(b, "CHECK POLARITY", 75.0, 35.0, B, 1.0)
    label(b, "REV", 86.45, 44.1, B, 1.0)
    # Bottom silkscreen is mirrored so it reads correctly from the bottom.
    label(b, f"TMR HALF COUPON REV {REV}", 19.0, 2.4, B, 1.0)
    label(b, "RAIL A  K1-K3  100nF bypass", 16.0, 4.9, B, 0.8)
    label(b, "RAIL B  K4-K6  10nF bypass", 32.5, 41.6, B, 0.8)
    label(b, "MUX A", 25.0, 6.6, B, 0.8); label(b, "MUX B", 29.0, 26.0, B, 0.8)
    label(b, "JLCJLCJLCJLC", 52.0, 47.5, B, 0.8)
    # Decoration goes on last, so it can keep clear of every mark above.
    decoration = silk_pattern.apply(b, ORIGIN, (W, H, RADIUS))
    b.BuildConnectivity()
    path = out / (STEM + ".kicad_pcb")
    if not k.SaveBoard(str(path), b, True):
        raise OSError(path)
    print(path.name, "footprints", len(list(b.GetFootprints())), "nets", len(nets))
    print("  decorative silkscreen", decoration)
    for ref in ("J1", "S1", "U7", "Q1"):
        print(" ", ref, {p.GetNumber(): at(ref, p.GetNumber()) for p in placed[ref].Pads() if p.GetNumber() in ("1", "2", "3", "24")})


if __name__ == "__main__":
    build()
