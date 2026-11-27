"""Planar mechanical layers in canonical XY -> analytic OpenCascade BReps in CAD XY."""

import math
import struct
from collections import Counter
from pathlib import Path
from build123d import Color, Compound, Face, Wire, extrude, export_stl
from shapely import set_precision
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

EPS = 0.00002  # Boolean volume audit threshold below is separate.
EMPTY = Polygon()


def disk(x, y, radius):
    return Point(x, y).buffer(radius, quad_segs=10)


def grow(poly, n):
    return poly.buffer(n, quad_segs=6, join_style="round")


def join(*polys):
    return unary_union([p for p in polys if not p.is_empty])


def snap(p):
    return set_precision(p, 0.00001)


def rect(x, y, w, h):
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def hex_nut(x, y, af):
    r = af / math.sqrt(3)
    return Polygon(
        [
            (x + r * math.cos(i * math.pi / 3), y + r * math.sin(i * math.pi / 3))
            for i in range(6)
        ]
    )


def panels(geo, low, high):
    """Extrude every filled island and every hole; input units mm, +Y palm."""
    if high <= low or geo.is_empty:
        return []
    geo = snap(geo)

    def wire(ring):
        return Wire.make_polygon(
            [(x, -y, low) for x, y in list(ring.coords)[:-1]], close=True
        )

    result = []
    for p in getattr(geo, "geoms", [geo]):
        if not isinstance(p, Polygon) or p.area < 1e-7:
            continue
        f = Face(wire(p.exterior), [wire(r) for r in p.interiors])
        result.extend(extrude(f, amount=high - low, dir=(0, 0, 1)).solids())
    return result


def compound_parts(items):
    items = [s for s in items if s is not None]
    return items[0] if len(items) == 1 else Compound(children=items)


def volume(shape):
    return abs(float(shape.volume))


def layered(layers, name, tint, single=True):
    solids = [s for z0, z1, geo in layers for s in panels(geo, z0, z1)]
    if not solids:
        raise ValueError(f"empty shape: {name}")
    result = solids[0].fuse(*solids[1:]).clean() if len(solids) > 1 else solids[0]
    if not result.is_valid:
        raise ValueError(f"invalid BRep: {name}")
    if single and len(result.solids()) != 1:
        raise ValueError(
            f"{name} has {len(result.solids())} disconnected solids, volumes {[round(s.volume, 2) for s in result.solids()]}"
        )
    if len(result.solids()) == 1:
        result = result.solids()[0]
    result.label = name
    result.color = Color(*tint)
    result._material_layers = [
        (z0, z1, snap(geo)) for z0, z1, geo in layers if not geo.is_empty
    ]
    return result


def prism(p, z0, z1, name, tint=(0.58, 0.65, 0.63)):
    s = compound_parts(panels(p, z0, z1))
    s.label = name
    s.color = Color(*tint)
    s._material_layers = [(z0, z1, snap(p))]
    return s


def common(a, b):
    # Cheap exact disjointness guard. Suspect pairs still go through actual OCCT volumetric intersection.
    la = getattr(a, "_material_layers", None)
    lb = getattr(b, "_material_layers", None)
    if la is None and a.children:
        return sum(common(x, b) for x in a.children)
    if lb is None and b.children:
        return sum(common(a, x) for x in b.children)
    aa, bb = a.bounding_box(), b.bounding_box()
    if any(
        x1 <= y0 + 1e-7 or y1 <= x0 + 1e-7
        for x0, x1, y0, y1 in zip(aa.min, aa.max, bb.min, bb.max)
    ):
        return 0.0

    def as_layer(bb):
        return [(bb.min.Z, bb.max.Z, box(bb.min.X, -bb.max.Y, bb.max.X, -bb.min.Y))]

    if not any(
        min(z1, t1) - max(z0, t0) > 1e-7
        and not p.disjoint(q)
        and p.intersection(q).area > 1e-8
        for z0, z1, p in (la or as_layer(aa))
        for t0, t1, q in (lb or as_layer(bb))
    ):
        return 0.0
    intersections = a.intersect(b)
    return sum(volume(s) for s in intersections or [] if s.solids())


def bounds(s):
    b = s.bounding_box()
    return [round(float(v), 5) for v in (*b.min, *b.max)]


def write_mesh(part, path: Path):
    """Verify the emitted binary STL itself, welding by exact float32 vertices."""
    if not export_stl(part, path, tolerance=0.035, angular_tolerance=0.18):
        raise ValueError(f"STL export failed: {path}")
    raw = path.read_bytes()
    n = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + 50 * n or n < 4:
        raise ValueError(f"invalid STL: {path}")
    directed = Counter()
    retained = []
    vertices = {}
    geom_tol = 0.00002

    def weld(a):
        cell = tuple(math.floor(v / geom_tol) for v in a)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in (-1, 0, 1):
                    for v in vertices.get((cell[0] + i, cell[1] + j, cell[2] + k), ()):
                        if math.dist(a, v) <= geom_tol:
                            return v
        vertices.setdefault(cell, []).append(a)
        return a

    for idx, (*values, _) in enumerate(struct.iter_unpack("<12fH", raw[84:])):
        a, b, c = (weld(tuple(values[i : i + 3])) for i in (3, 6, 9))
        if len({a, b, c}) != 3:
            continue  # Float32 quantization can collapse an OCC tessellation edge to zero length.
        retained.append(struct.pack("<12fH", *values[:3], *a, *b, *c, 0))
        directed.update([(a, b), (b, c), (c, a)])
    bad = sum(v != 1 or directed[(b, a)] != 1 for (a, b), v in directed.items())
    if bad:
        raise ValueError(
            f"{path}: {bad} open, non-manifold or inconsistently wound mesh edges"
        )
    path.write_bytes(raw[:80] + struct.pack("<I", len(retained)) + b"".join(retained))
    return len(retained)
