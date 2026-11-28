#!/usr/bin/python3
"""Decorative silkscreen: a zoomed crop of the quadtree Truchet pattern on both sides.

  python3 tools/silk_pattern.py    crop silkscreen-patterns/svg/03_quadtree_truchet.svg (repo root) into
                                   build/silk-pattern.json, in board millimetres
  apply(board, origin, size)       called by place_board.py inside KiCad's Python; trims the pattern
                                   against the board and adds what is left to F.SilkS and B.SilkS

The pattern never wins against anything functional. The strokes are turned into filled areas, and
everything within CLEAR of a pad, a hole, the courtyard of a soldered part, another silkscreen mark or
the board edge is cut out of them. Slivers thinner than MIN_FEATURE and islands smaller than MIN_AREA
or shorter than MIN_LENGTH are dropped, so what reaches the fab is ink it can print.
"""
import json
import math
import re
from design import ROOT, uid

SOURCE = ROOT.parent.parent / "silkscreen-patterns" / "svg" / "03_quadtree_truchet.svg"
CROPPED = ROOT / "build" / "silk-pattern.json"
ZOOM = 2.0                                  # source strokes 0.39 / 0.78 / 1.40 mm print at 0.78 / 1.56 / 2.80 mm
CROP = {"F.SilkS": (90.0, 95.0), "B.SilkS": (300.0, 150.0)}   # top-left corner of each window in the source, mm
W, H, RADIUS = 92.0, 50.0, 2.0              # board outline; place_board.py asserts these match its own
CLEAR = 0.30                                # stroke edge to pads, holes, courtyards and other silkscreen
TEXT_CLEAR = 0.45                           # stroke edge to the box around a text label
EDGE_CLEAR = 0.60                           # stroke edge to the board edge
MIN_FEATURE = 0.30                          # thinnest ink kept (JLCPCB silkscreen line minimum is 0.15 mm)
MIN_AREA, MIN_LENGTH = 4.0, 4.5             # smallest island kept: mm^2, and mm along its longer side
MIN_GAP = 1.0                               # channels between keepouts narrower than this stay empty
ARC_ERROR = 0.005                           # chord error when curves become polygons
OPEN_SEAT = ("ProMicro",)                  # switch courtyards keep both decorative and functional ink off the front seats
ARC = re.compile(r'd="M\s*([-\d.]+),([-\d.]+) A\s*([-\d.]+),[-\d.]+ 0 0 ([01]) ([-\d.]+),([-\d.]+)"[^>]*?'
                 r'stroke-width="([-\d.]+)"')


def crop():
    """Arcs as (centre x, centre y, radius, start angle, signed sweep, stroke width) in board mm."""
    found = ARC.findall(SOURCE.read_text())
    if len(found) < 1000:
        raise ValueError(f"{SOURCE}: expected the pattern's arcs, parsed {len(found)}")
    out = {}
    for layer, (ox, oy) in CROP.items():
        arcs = []
        for x1, y1, r, sweep, x2, y2, width in found:
            x1, y1, x2, y2 = ((float(x1) - ox) * ZOOM, (float(y1) - oy) * ZOOM,
                              (float(x2) - ox) * ZOOM, (float(y2) - oy) * ZOOM)
            r, half = float(r) * ZOOM, float(width) * ZOOM / 2
            dx, dy = x2 - x1, y2 - y1; chord = math.hypot(dx, dy)
            h = math.sqrt(max(r * r - chord * chord / 4, 0.0)) * (1 if sweep == "1" else -1)
            cx, cy = (x1 + x2) / 2 - h * dy / chord, (y1 + y2) / 2 + h * dx / chord
            if not (-r - half < cx < W + r + half and -r - half < cy < H + r + half):
                continue
            a0, a1 = math.atan2(y1 - cy, x1 - cx), math.atan2(y2 - cy, x2 - cx)
            turn = (a1 - a0) % (2 * math.pi) if sweep == "1" else -((a0 - a1) % (2 * math.pi))
            arcs.append([round(v, 4) for v in (cx, cy, r, a0, turn, 2 * half)])
        out[layer] = arcs
    CROPPED.parent.mkdir(exist_ok=True)
    CROPPED.write_text(json.dumps({"source": SOURCE.name, "zoom": ZOOM, "crop": CROP, "arcs": out}))
    print(CROPPED.name, {layer: len(a) for layer, a in out.items()}, "arcs near the board")


def keepouts(board, layer, origin):
    """(rectangles, circles) the pattern must stay CLEAR of on one silkscreen layer, in board mm."""
    import pcbnew as k
    copper, court = (k.F_Cu, k.F_CrtYd) if layer == k.F_SilkS else (k.B_Cu, k.B_CrtYd)
    rects, circles = [], []

    def box(item_box, grow):
        rects.append((k.ToMM(item_box.GetLeft()) - origin[0] - grow, k.ToMM(item_box.GetTop()) - origin[1] - grow,
                      k.ToMM(item_box.GetRight()) - origin[0] + grow, k.ToMM(item_box.GetBottom()) - origin[1] + grow))

    for f in board.GetFootprints():
        name = f.GetFPIDAsString().split(":")[-1]
        for p in f.Pads():
            through = p.GetAttribute() in (k.PAD_ATTRIB_PTH, k.PAD_ATTRIB_NPTH)
            if not through and not p.IsOnLayer(copper):
                continue
            if p.GetShape(k.F_Cu) == k.PAD_SHAPE_CIRCLE:
                q = p.GetPosition(); d = max(p.GetSizeX(), p.GetDrillSizeX())
                circles.append((k.ToMM(q.x) - origin[0], k.ToMM(q.y) - origin[1], k.ToMM(d) / 2 + CLEAR))
            else:
                box(p.GetBoundingBox(), CLEAR)
        for g in list(f.GraphicalItems()) + list(f.GetFields()):
            if g.GetLayer() == layer and (g.GetClass() != "PCB_FIELD" or g.IsVisible()):
                box(g.GetBoundingBox(), TEXT_CLEAR if "TEXT" in g.GetClass() else CLEAR)
        yard = f.GetCourtyard(court)
        if yard.OutlineCount() and not name.startswith(OPEN_SEAT) and (f.GetLayer() == copper or name.startswith("MountingHole")):
            if name.startswith("MountingHole"):       # room for the screw head or standoff on either side
                q = f.GetPosition()
                circles.append((k.ToMM(q.x) - origin[0], k.ToMM(q.y) - origin[1], k.ToMM(yard.BBox().GetWidth()) / 2 + CLEAR))
            else:
                box(yard.BBox(), CLEAR)
    for d in board.GetDrawings():
        if d.GetLayer() == layer:
            box(d.GetBoundingBox(), TEXT_CLEAR if "TEXT" in d.GetClass() else CLEAR)
    return rects, circles


def stroke(cx, cy, r, a, sweep, half):
    """Outline of a round-capped arc stroke: out along the outer edge, around the end, back along the inner edge."""
    assert r > half
    def run(radius, x, y, a0, turn):
        n = max(2, math.ceil(abs(turn) / (2 * math.acos(1 - ARC_ERROR / radius))))
        return [(x + radius * math.cos(a0 + turn * i / n), y + radius * math.sin(a0 + turn * i / n)) for i in range(n)]
    b = a + sweep; flip = math.copysign(math.pi, sweep)
    return (run(r + half, cx, cy, a, sweep) + run(half, cx + r * math.cos(b), cy + r * math.sin(b), b, flip)
            + run(r - half, cx, cy, b, -sweep) + run(half, cx + r * math.cos(a), cy + r * math.sin(a), a + math.pi, flip))


def apply(board, origin, size):
    """Add the trimmed pattern to both silkscreen layers. Call after every other silkscreen item exists."""
    import pcbnew as k
    assert size == (W, H, RADIUS), "silk_pattern.py and place_board.py disagree on the board outline"
    iu, err, round_ = k.FromMM, k.FromMM(ARC_ERROR), k.CORNER_STRATEGY_ROUND_ALL_CORNERS

    def polygon(points):
        poly = k.SHAPE_POLY_SET(); poly.NewOutline()
        for x, y in points:
            poly.Append(iu(origin[0] + x), iu(origin[1] + y))
        return poly

    def disc(x, y, r, n=64):                 # circumscribed, so the polygon never sits inside the circle
        r /= math.cos(math.pi / n)
        return polygon((x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n))

    r = RADIUS - EDGE_CLEAR; e = EDGE_CLEAR; corner = []
    for cx, cy, a0 in ((W - e - r, e + r, -90), (W - e - r, H - e - r, 0), (e + r, H - e - r, 90), (e + r, e + r, 180)):
        corner += [(cx + r * math.cos(math.radians(a0 + i * 5)), cy + r * math.sin(math.radians(a0 + i * 5))) for i in range(19)]
    inside = polygon(corner)

    data = json.loads(CROPPED.read_text()); total = {}
    for name, arcs in data["arcs"].items():
        layer = {"F.SilkS": k.F_SilkS, "B.SilkS": k.B_SilkS}[name]
        rects, circles = keepouts(board, layer, origin); blocked = k.SHAPE_POLY_SET()
        for x0, y0, x1, y1 in rects:
            blocked.BooleanAdd(polygon(((x0, y0), (x1, y0), (x1, y1), (x0, y1))))
        for x, y, radius in circles:
            blocked.BooleanAdd(disc(x, y, radius))
        blocked.Inflate(iu(MIN_GAP / 2), round_, err); blocked.Deflate(iu(MIN_GAP / 2), round_, err)
        ink = k.SHAPE_POLY_SET()
        for cx, cy, radius, a, sweep, width in arcs:
            ink.BooleanAdd(polygon(stroke(cx, cy, radius, a, sweep, width / 2)))
        ink.BooleanIntersection(inside); ink.BooleanSubtract(blocked)
        ink.Deflate(iu(MIN_FEATURE / 2), round_, err); ink.Inflate(iu(MIN_FEATURE / 2), round_, err)
        ink.BooleanSubtract(blocked)         # rounding the corners back out must not step into a keepout
        n = 0; area = 0.0
        for i in range(ink.OutlineCount()):
            island = k.SHAPE_POLY_SET(ink.Polygon(i)); size_mm2 = island.Area() / 1e12
            box = island.BBox()
            if size_mm2 < MIN_AREA or k.ToMM(max(box.GetWidth(), box.GetHeight())) < MIN_LENGTH:
                continue
            island.Fracture()                # a silkscreen polygon cannot carry holes; join them to the outline
            assert island.OutlineCount() == 1 and not island.HasHoles()
            s = k.PCB_SHAPE(board); s.SetShape(k.SHAPE_T_POLY); s.SetPolyShape(island); s.SetFilled(True)
            s.SetLayer(layer); s.SetWidth(0); s.SetUuid(k.KIID(uid(f"silk-pattern/{name}/{n}"))); board.Add(s)
            n += 1; area += size_mm2
        total[name] = f"{n} areas, {area:.0f} mm2"
    return total


if __name__ == "__main__":
    crop()
