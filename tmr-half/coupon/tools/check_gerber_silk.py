#!/usr/bin/env python3
"""Read the plotted silk back; check stroke apertures, edge, and empty switch seats."""
import json
from pathlib import Path

from gerbonara import GerberFile
from gerbonara.graphic_objects import Arc, Flash, Line, Region
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
MIN_STROKE, MIN_TEXT, MIN_EDGE = 0.15, 1.0, 0.30


def check(plots, native):
    result, problems = {}, []
    # Plot coordinates use the native absolute datum with an inverted Y.
    # Sample the specified 2 mm corners finely enough to resolve 0.001 mm.
    outline = box(102, -148, 190, -102).buffer(2, quad_segs=64)
    for side, extension in (("F", "gto"), ("B", "gbo")):
        artwork = GerberFile.open(plots / f"tmr-coupon-{side}_Silkscreen.{extension}")
        widths, dark = [], []
        for o in artwork.objects:
            # Measure positive ink before the downstream solder-mask subtraction.
            # This is conservative for edge, seat, and tented via checks.
            if not o.polarity_dark:
                continue
            if isinstance(o, Region):
                if any(c is not None for c in getattr(o, "arc_centers", ())):
                    raise ValueError("Unexpected arc in silk polygon")
                dark.append(Polygon(o.outline).buffer(0))
            elif isinstance(o, (Line, Arc)):
                width = o.aperture.diameter
                widths.append(width)
                lines = [o] if isinstance(o, Line) else list(o.approximate(max_error=0.001))
                dark.extend(LineString([(l.x1, l.y1), (l.x2, l.y2)]).buffer(width/2, quad_segs=10)
                            for l in lines)
            elif isinstance(o, Flash) and hasattr(o.aperture, "diameter"):
                dark.append(Point(o.x, o.y).buffer(o.aperture.diameter/2))
            else:
                raise ValueError(f"Unsupported Gerber ink: {o}")
        ink = unary_union(dark)
        edge = ink.distance(outline.boundary) if outline.covers(ink) else 0
        text = native["silk_text"][side]
        seats = {r: ink.intersection(box(x-7, y-7, x+7, y+7)).area
                 for r, (x,y) in native["switches"].items()} if side == "F" else {}
        via_count = sum(ink.intersects(Point(x,y).buffer(drill/2)) for x,y,drill in native["vias"])
        stroke = min(widths)
        text_height = min(h for _, h, _ in text)
        for condition, label in ((stroke < MIN_STROKE, "undersize plotted stroke"),
                                 (text_height < MIN_TEXT or any(w < MIN_STROKE for _, _, w in text),
                                  "undersize native text or stroke"),
                                 (edge < MIN_EDGE, "ink too close to board edge"),
                                 (any(v > 1e-6 for v in seats.values()), "ink in switch seat")):
            if condition:
                problems.append(f"{side}: {label}")
        result[side] = dict(minimum_plot_stroke_mm=round(stroke, 4), minimum_text_height_mm=text_height,
                            ink_to_edge_mm=round(edge, 4), via_holes_under_ink=via_count,
                            switch_seat_ink_mm2={r: round(v, 6) for r,v in seats.items()})
    return dict(layers=result, problems=problems, passed=not problems)


if __name__ == "__main__":
    native = json.loads((ROOT / "build" / "native.json").read_text())
    report = check(ROOT / "fab" / "gerbers", native)
    (ROOT / "reports" / "gerber-silk.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Gerber silk:", json.dumps(report))
    raise SystemExit(0 if report["passed"] else 1)
