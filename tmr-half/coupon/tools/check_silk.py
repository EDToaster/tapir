#!/usr/bin/python3
"""Measure the decorative silkscreen on the routed board, independently of the code that drew it.

Rebuilds the pads, holes, footprint silkscreen and text labels of each side as polygons with KiCad's
own geometry, then finds the nearest ink. Fails if the pattern comes closer than the limits below.
"""
import json
import pcbnew as k
from design import ROOT, STEM

NEAREST_MARK, NEAREST_EDGE = 0.29, 0.59      # mm; silk_pattern.py aims for 0.30 and 0.60


def measure():
    b = k.LoadBoard(str(ROOT / (STEM + ".kicad_pcb"))); err = k.FromMM(0.002); out = {}
    edge = b.GetBoardEdgesBoundingBox()
    for layer, copper in ((k.F_SilkS, k.F_Cu), (k.B_SilkS, k.B_Cu)):
        ink = [d.GetPolyShape() for d in b.GetDrawings()
               if d.GetClass() == "PCB_SHAPE" and d.GetShape() == k.SHAPE_T_POLY and d.GetLayer() == layer]
        assert ink, "no decorative silkscreen on " + b.GetLayerName(layer)
        other = k.SHAPE_POLY_SET()
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.IsOnLayer(copper):
                    p.TransformShapeToPolygon(other, copper, 0, err, k.ERROR_OUTSIDE)
                if p.GetDrillSizeX():
                    p.TransformHoleToPolygon(other, 0, err, k.ERROR_OUTSIDE)
            for g in f.GraphicalItems():
                if g.GetLayer() == layer:
                    g.TransformShapeToPolygon(other, layer, 0, err, k.ERROR_OUTSIDE)
        for d in b.GetDrawings():
            if d.GetLayer() == layer and d.GetClass() == "PCB_TEXT":
                d.TransformShapeToPolygon(other, layer, 0, err, k.ERROR_OUTSIDE)
        other.Simplify()
        mark = min(other.SquaredDistance(p.Outline(i).CPoint(j)) for p in ink
                   for i in range(p.OutlineCount()) for j in range(p.Outline(i).PointCount())) ** 0.5
        rim = min(min(q.GetLeft() - edge.GetLeft(), edge.GetRight() - q.GetRight(),
                      q.GetTop() - edge.GetTop(), edge.GetBottom() - q.GetBottom()) for q in (p.BBox() for p in ink))
        out[b.GetLayerName(layer)] = {"areas": len(ink), "ink_mm2": round(sum(p.Area() for p in ink) / 1e12, 1),
                                      "nearest_pad_hole_or_mark_mm": round(k.ToMM(int(mark)), 3),
                                      "nearest_board_edge_mm": round(k.ToMM(rim), 3)}
    ok = all(v["nearest_pad_hole_or_mark_mm"] >= NEAREST_MARK and v["nearest_board_edge_mm"] >= NEAREST_EDGE
             for v in out.values())
    (ROOT / "reports" / "silk-clearance.json").write_text(json.dumps({"layers": out, "pass": ok}, indent=1) + "\n")
    print("decorative silkscreen:", json.dumps(out))
    if not ok:
        raise SystemExit("decorative silkscreen is too close to a pad, hole, mark or the board edge")


if __name__ == "__main__":
    measure()
