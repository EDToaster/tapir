"""Editable mechanical design. Coordinates fed to the modeling helpers are product/design XY."""

import math
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Polygon, box
from kernel import EMPTY, disk, grow, hex_nut, join, layered, rect

# Prototype stock/clearances, mm. These are proposed process allowances, not measurements.
FLOOR = -6.8
FLOOR_TOP = -4.65
PCBBOT = -1.6
PCB_NUT_TOP = -4.20
CASE_NUT_TOP = -3.72
PCB_RADIAL = 0.50
WALL = 1.8
BEZEL_BOTTOM = 1.15
BEZEL_TOP = 2.50
SHELF_Z = (
    5.40  # 1.10 above 4.30 supplier maximum Z, including the explicit insulation budget
)
SHELF_TOP = 6.65
HOOD_INNER = 12.10
HOOD_TOP = 13.55
PLASTIC = (0.25, 0.33, 0.32)
LID = (0.76, 0.76, 0.69)
ACCENT = (0.66, 0.38, 0.22)


def poly(r):
    return Polygon(r["polygon"])


def local_shape(record, *args):
    return translate(
        rotate(rect(0, 0, args[2], args[3]), record.get("a", 0), origin=(0, 0)),
        *world(record, *args[:2]),
    )


def world(r, u, v):
    a = math.radians(r.get("a", 0))
    return r["x"] + math.cos(a) * u - math.sin(a) * v, r["y"] + math.sin(
        a
    ) * u + math.cos(a) * v


def rect_axis(x, y, ux, uy, width, d0, d1):
    vx, vy = -uy, ux
    return Polygon(
        [
            (x + ux * d + vx * w, y + uy * d + vy * w)
            for d, w in (
                (d0, -width / 2),
                (d1, -width / 2),
                (d1, width / 2),
                (d0, width / 2),
            )
        ]
    )


def points_in_ring(outline, forbidden):
    """Three distinct screw seats entirely outside the PCB, away from moving/access features."""
    ring = grow(outline, 3.45).exterior
    candidates = [ring.interpolate(i * 1.75) for i in range(int(ring.length / 1.75))]
    candidates = [p for p in candidates if p.distance(forbidden) > 4.35]
    if len(candidates) < 3:
        raise ValueError("no eligible enclosure closures")
    # Keep PCB and case fasteners independent. Pick the largest dispersed set greedily.
    anchor = max(candidates, key=lambda p: p.distance(outline.centroid))
    seats = [anchor]
    for _ in range(2):
        seats.append(max(candidates, key=lambda p: min(p.distance(q) for q in seats)))
    return [(p.x, p.y) for p in seats]


def layout(h):
    c = h["components"]
    outline = Polygon(h["outline"])
    holes = h["mountingHoles"]
    case = type("Layout", (), {})()
    q = case
    q.h = h
    q.c = c
    q.outline = outline
    q.holes = holes
    q.records = h["solids"]
    q.by_id = {s["id"]: s for s in q.records}
    q.pack = c["battery"]
    bx, by = q.pack["x"], q.pack["y"]
    q.pack_max = rect(bx, by, 12.3, 32)
    q.pack_space = grow(q.pack_max, 0.80)  # per-side room outside supplier extreme
    q.cassette = grow(q.pack_space, 1.20)
    q.hood_space = grow(q.cassette, 0.35)
    if h["hand"] == "right":
        q.hood_space = join(q.hood_space, translate(q.hood_space, 0, 0.60))
    q.hood = grow(q.hood_space, 1.35)
    q.jst_relief = grow(
        join(poly(c["batteryConnectorCourt"]), poly(c["batteryPlug"])), 0.45
    )
    q.cassette = q.cassette.difference(q.jst_relief)
    q.exit_sign = 1 if h["hand"] == "left" else -1
    q.end = by + q.exit_sign * 16
    # Width is deliberately larger than the loose PH plug: cable is never threaded through a pin-hole.
    q.lead_gate = rect(bx, q.end + q.exit_sign * 2.5, 9.5, 8.5)
    q.mouth = h["usbMouth"]
    u, v = q.mouth["direction"]
    q.usb = rect_axis(q.mouth["x"], q.mouth["y"], u, v, 12.35, 0, 38)
    # Shell gauge uses USB-IF overmold maximum (12.35 × 6.5), not the 9-mm receptacle.
    q.usb_cut = grow(q.usb, 0.55)
    ps = c["powerSwitch"]
    q.power_path = local_shape(ps, 0, 5.8, 8.5, 11.8)
    q.switch_union = join(*[Polygon(s["bodyPolygon"]) for s in h["switches"]])
    q.key_holes = grow(q.switch_union, 0.38)
    q.keycaps = join(*[Polygon(s["capPolygon"]) for s in h["switches"]])
    q.mount_open = join(
        *[disk(s["x"], s["y"], s["toolDiameter"] / 2 + 0.30) for s in holes]
    )
    q.bridge = poly(c["bridge"]) if "bridge" in c else EMPTY
    q.bridge_tabs = EMPTY
    q.feet = EMPTY
    if "bridge" in c:
        q.feet = join(*[poly(p) for p in c["feet"]])
        # Palmward ears on the two forward posts; their tips are held UNDER the removable bezel.
        mxy = sorted(c["feet"], key=lambda a: a["y"], reverse=True)[:2]
        tab_end = q.bridge.bounds[3] + 2.15
        q.bridge_tabs = join(
            *[box(p["x"] - 1.02, p["y"] - 0.8, p["x"] + 1.02, tab_end) for p in mxy]
        )
    q.driver = poly(c["driver"]) if "driver" in c else EMPTY
    q.driver_cavity = grow(q.driver, 0.6)
    q.driver_hood = grow(q.driver_cavity, 1.25)
    # Access may extend beyond the outline. Never leave a wall across the plug/power approach.
    jst = join(poly(c["batteryConnectorCourt"]), poly(c["batteryPlug"]))
    site = join(
        q.usb_cut,
        q.power_path,
        jst,
        q.hood,
        q.bridge,
        q.driver_hood,
        *[poly(x["paddle"]) for x in h["buttons"]],
        q.mount_open,
    )
    q.seats = points_in_ring(outline, site)
    ears = join(*[disk(x, y, 3.40) for x, y in q.seats])
    q.outer = join(grow(outline, PCB_RADIAL + WALL), ears)
    q.bosses = join(*[disk(x["x"], x["y"], x["bossDiameter"] / 2) for x in holes])
    q.pcb_seats = [(s["x"], s["y"]) for s in holes]
    q.all_seats = q.pcb_seats + q.seats
    q.screw_bores = join(*[disk(x, y, 1.20) for x, y in q.all_seats])
    q.case_bores = join(*[disk(x, y, 1.20) for x, y in q.seats])
    q.nut_pockets = join(*[hex_nut(x, y, 4.42) for x, y in q.all_seats])
    q.case_nut_pockets = join(*[hex_nut(x, y, 4.42) for x, y in q.seats])
    q.nut_lower_boss = join(*[disk(x, y, 3.20) for x, y in q.pcb_seats])
    q.inside = grow(outline, PCB_RADIAL)
    q.rim = q.outer.difference(q.inside)
    q.aux = join(
        *[
            poly(v)
            for k, v in c.items()
            if k
            in (
                "xiao",
                "usbShell",
                "batteryConnectorCourt",
                "batteryPlug",
                "powerSwitchCourt",
                "powerLever",
                "driverHeader",
                "driverElectronics",
            )
        ]
    )
    q.holes_top = join(
        q.key_holes,
        grow(q.aux, 0.55),
        q.usb_cut,
        q.power_path,
        q.mount_open,
        grow(q.bridge, 0.42),
        q.driver_cavity,
        q.hood_space,
        q.case_bores,
    )
    q.beams = []
    q.button_holes = EMPTY
    for b in h["buttons"]:
        # One-piece cantilever; the small top pad loads the switch from above, with no preload.
        hole = local_shape(b, 0, -0.9, 9.6, 8.4)
        root = local_shape(b, 0, -5.45, 5.0, 1.85)
        beam = local_shape(b, 0, -2.45, 3.0, 6.65)
        top = local_shape(b, 0, 0, 8.0, 5.0)
        tip = disk(b["x"], b["y"], 0.95)
        q.beams.append((root, beam, top, tip))
        q.button_holes = join(q.button_holes, hole)
    return q


def tray(q, emit=layered):
    floors = q.outer.difference(q.nut_pockets)
    bore = q.screw_bores
    # Nuts loaded from underside, capped by material to resist screw tension, removable when unbolted.
    low = q.rim.union(q.bosses).difference(bore)
    beef = join(q.rim, q.nut_lower_boss)
    zones = [
        (FLOOR, FLOOR_TOP, floors),
        (FLOOR_TOP, PCB_NUT_TOP, beef.difference(q.nut_pockets)),
        (PCB_NUT_TOP, CASE_NUT_TOP, beef.difference(join(q.case_nut_pockets, bore))),
        (CASE_NUT_TOP, PCBBOT, low),
        (PCBBOT, -0.65, q.rim.difference(bore)),
        (-0.65, 0, q.rim.difference(join(bore, q.usb_cut, q.power_path))),
    ]
    return emit(zones, "bottom_tray", PLASTIC)


def cassette(q, wire_slot=EMPTY, emit=layered):
    p = q.pack
    bx, by = p["x"], p["y"]
    walls = q.cassette.difference(q.pack_space).difference(q.lead_gate)
    # A smooth obround island makes a reusable wire store. Insulated pairs are laid beside it, never clamped.
    mid = LineString([(bx, by - 6.0), (bx, by + 6.0)])
    spindle = mid.buffer(2.80, quad_segs=8)
    q.spindle = spindle
    # U-shaped exit, open at one end, keeps both the foil and the lead unpinched.
    slot = rect(bx, q.end + q.exit_sign * 2.75, 8.0, 5.25)
    shelf = q.cassette.difference(slot)
    return emit(
        [
            (0, 1.85, walls.difference(wire_slot)),
            (1.85, SHELF_Z, walls),
            (SHELF_Z, SHELF_TOP, shelf),
            (SHELF_TOP, 10.25, spindle),
        ],
        "pouch_separator_and_winding_form",
        ACCENT,
    )


def bridge(q, emit=layered):
    c = q.c
    b = c["bridge"]
    holes = [disk(o["x"], o["y"], 0.72) for o in c["sensorHoles"]]
    # Four isolated lands allow non-conductive bond or a revised electrical interposer. No cap or screw through the active sensor.
    deck = q.bridge.difference(join(*holes))
    # Pair each side's legs with an edge-length gusset rib; keep it outside the controller and the reset/antenna end.
    feet = c["feet"]
    xs = sorted({f["x"] for f in feet})
    ys = [f["y"] for f in feet]
    ribs = join(*[box(x - 0.85, min(ys) - 0.8, x + 0.85, max(ys) + 0.8) for x in xs])
    return emit(
        [
            (0, 0.9, join(q.feet, q.bridge_tabs)),
            (0.9, 4.05, q.feet),
            (4.05, b["bottom"], join(q.feet, ribs)),
            (b["bottom"], b["top"], deck),
        ],
        "captive_pointer_bridge",
        ACCENT,
    )


def cover(q, wire_slot=EMPTY, analog_slot=EMPTY, emit=layered):
    full = q.outer.difference(
        join(q.holes_top, q.button_holes, wire_slot, analog_slot, q.lead_gate)
    )
    # Castellated cover extends into the seam but never enters the board opening.
    rim = q.rim.difference(
        join(
            q.usb_cut, q.power_path, q.case_bores, q.hood_space, wire_slot, q.lead_gate
        )
    )
    hoodring = (
        q.hood.difference(q.hood_space).difference(q.lead_gate).difference(q.jst_relief)
    )
    # The pouch cassette top is captured by an upper ledge, not by the foil.
    ledge = (
        q.hood.difference(grow(q.cassette, -0.65))
        .difference(q.lead_gate)
        .difference(q.jst_relief)
    )
    ledge = join(hoodring, ledge.intersection(rect(q.pack["x"], q.pack["y"], 22, 8)))
    driver_wall = q.driver_hood.difference(q.driver_cavity).difference(analog_slot)
    # Shelf above driver needs a relief on the signal-harness side; the bare driver remains service removable.
    zones = [
        (0, BEZEL_BOTTOM, rim),
        (
            BEZEL_BOTTOM,
            BEZEL_TOP,
            join(full, hoodring.difference(wire_slot), driver_wall),
        ),
    ]
    if not driver_wall.is_empty:
        zones.extend([(BEZEL_TOP, 4.25, driver_wall), (4.25, 5.55, q.driver_hood)])
    zones.extend(
        [
            (BEZEL_TOP, SHELF_TOP + 0.32, hoodring),
            (SHELF_TOP + 0.32, SHELF_TOP + 1.55, ledge),
            (SHELF_TOP + 1.55, HOOD_INNER, hoodring),
            (HOOD_INNER, HOOD_TOP, q.hood),
        ]
    )
    # The roots are supported on the removable bezel. Top 4.5, under-tip 2.65, nominal free gap 0.15.
    if q.beams:
        roots, beams, tops, tips = [join(*g) for g in zip(*q.beams)]
        zones.extend(
            [
                (BEZEL_TOP, 2.65, roots),
                (2.65, 3.3, join(roots, tips)),
                (3.3, 4.0, join(roots, beams, tops)),
                (4.0, 4.50, tops),
            ]
        )
    return emit(zones, "service_bezel_and_hood", LID)
