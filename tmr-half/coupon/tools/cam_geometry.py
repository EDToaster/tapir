"""Independent outline and geometry helpers for mm Gerber read-back."""
from gerbonara.graphic_objects import Arc, Line
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union


def linework(o):
    if isinstance(o, Arc):
        return [*o.approximate(max_error=0.0002)]
    if isinstance(o, Line):
        return [o]
    raise ValueError(f"Non-line/arc Gerber object in outline: {type(o).__name__}")


def outline_polygon(gerber):
    segments = [((round(t.x1, 6), round(t.y1, 6)), (round(t.x2, 6), round(t.y2, 6)))
                for o in gerber.objects for t in linework(o)]
    endpoints = {}
    for a, b in segments:
        endpoints[a] = endpoints.get(a, 0) + 1
        endpoints[b] = endpoints.get(b, 0) + 1
    if not segments or any(n != 2 for n in endpoints.values()):
        raise ValueError("Gerber outline is not closed or branches")
    polygons = list(polygonize(LineString(p) for p in segments))
    if len(polygons) != 1 or not polygons[0].is_valid or polygons[0].interiors:
        raise ValueError("Gerber outline is not a single simple exterior loop")
    return polygons[0]


def copper_shape(object_):
    # KiCad emits round path apertures, macro/standard pad flashes and
    # fractured fill polygons. Repair the latter's zero-width joining slits.
    g = None
    for p in object_.to_primitives():
        poly = Polygon(p.to_arc_poly().approximate_arcs(max_error=0.0001).outline).buffer(0)
        if p.polarity_dark:
            g = poly if g is None else unary_union((g, poly))
        elif g is not None:
            g = g.difference(poly)
    if g is None or g.is_empty:
        raise ValueError(f"No copper geometry for {type(object_).__name__}")
    return g
