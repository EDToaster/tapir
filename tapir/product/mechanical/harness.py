"""Generate and audit the PKCELL lead lane (wire is installed, never shortened)."""

import heapq, math
import numpy as np
from shapely.geometry import LineString
from shapely.prepared import prep
from kernel import disk, grow, join
from design import poly, world


def route_grid(area, start, end):
    """8-connected routing inside a pre-eroded corridor; use line-of-sight to remove grid wiggles."""
    ok = prep(area)
    pitch = 0.75

    def near(p):
        a, b = p
        candidates = []
        for i in range(round(a / pitch) - 3, round(a / pitch) + 4):
            for j in range(round(b / pitch) - 3, round(b / pitch) + 4):
                q = (i * pitch, j * pitch)
                if ok.covers(LineString([p, q])):
                    candidates.append((math.dist(p, q), i, j))
        if not candidates:
            raise ValueError(f"wire endpoint falls outside free routing region: {p}")
        return min(candidates)[1:]

    first, last = near(start), near(end)
    back = {first: None}
    g = {first: 0.0}
    heap = [(0.0, 0.0, first)]
    while heap:
        _, d, p = heapq.heappop(heap)
        if p == last:
            break
        if d != g[p]:
            continue
        for dx, dy in (
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ):
            s = (p[0] + dx, p[1] + dy)
            dd = d + math.hypot(dx, dy)
            if dd >= g.get(s, math.inf):
                continue
            if not ok.covers(
                LineString([(p[0] * pitch, p[1] * pitch), (s[0] * pitch, s[1] * pitch)])
            ):
                continue
            g[s] = dd
            back[s] = p
            heapq.heappush(heap, (dd + math.dist(s, last), dd, s))
    if last not in back:
        raise ValueError(f"no wire route from {start} to {end}")
    points = []
    p = last
    while p is not None:
        points.append((p[0] * pitch, p[1] * pitch))
        p = back[p]
    points = [start, *reversed(points), end]
    out = [points[0]]
    while len(points) > 1:
        j = len(points) - 1
        while j > 1 and not ok.covers(LineString([out[-1], points[j]])):
            j -= 1
        out.append(points[j])
        points = points[j:]
    return out


def wire_plan(q):
    c = q.c
    p = q.pack
    sg = q.exit_sign
    bx = p["x"]
    # exit anchors are design hypotheses, not drawing datums of individual insulated strands.
    start = (bx + (2.40 if q.h["hand"] == "right" else -2.40), q.end + sg * 2.65)
    j = c["batteryConnector"]
    # Back of the seated plug, not the far tip of its full withdrawal gauge.
    end = world(j, 0, 9.7)
    obstacles = join(
        q.switch_union,
        q.mount_open,
        q.driver,
        poly(c["powerSwitchCourt"]),
        poly(c["xiao"]),
        q.pack_space,
        poly(c["batteryConnector"]),
        *[poly(b) for b in q.h["buttons"]],
    )
    field = q.outline.buffer(0.45).difference(grow(obstacles, 1.40))
    route = route_grid(field, start, end)
    # Full JST withdrawal is a separate, disconnected service operation. Stow only wire remaining after the run.
    line = LineString(route)
    reserve = 105 - line.length
    # Assembly includes a capped winding form: centerline at 4.2 radius, two straight 12 mm spans per turn.
    turn = 2 * 12 + 2 * math.pi * 4.2
    return {
        "centerlineXY": [list(v) for v in route],
        "lengthPlan_mm": round(line.length, 3),
        "remainingOf105BeforeRisesAndBends_mm": round(reserve, 3),
        "leadNominal_mm": 105,
        "wireEnvelopeWidth_mm": 2.2,
        "wireEnvelopeZ": [0.30, 1.50],
        "minimumScreenedHorizontalClearance_mm": round(
            line.distance(obstacles) - 1.1, 3
        ),
        "formCenterlineRadius_mm": 4.2,
        "windingCenterlinePerTurn_mm": round(turn, 3),
        "twoTurnNominalCapacity_mm": round(2 * turn, 3),
        "passed105mmHarnessFit": False,
        "scope": "Candidate 2D run at Z0.30..1.50 plus segregated coil chamber; actual insulated exit, PH back, rises, bend radius, pull and full 105-mm fitted harness remain sample gates.",
    }, line.buffer(1.10, quad_segs=6)


def fillet3(points, radius=1.6):
    """Tangential circular bends, adaptively shortened only where adjacent straight spans demand it."""
    v = [np.array(p, dtype=float) for p in points]
    out = [v[0]]
    radii = []
    for i in range(1, len(v) - 1):
        a, p, b = v[i - 1 : i + 2]
        lu = np.linalg.norm(p - a)
        lv = np.linalg.norm(b - p)
        if min(lu, lv) < 1e-7:
            continue
        u = (p - a) / lu
        w = (b - p) / lv
        ang = math.acos(float(np.clip(u @ w, -1, 1)))
        if ang < 0.025:
            out.append(p)
            continue
        tangent = min(radius * math.tan(ang / 2), 0.44 * lu, 0.44 * lv)
        rad = tangent / math.tan(ang / 2)
        axis = np.cross(u, w)
        axis /= np.linalg.norm(axis)
        first = p - u * tangent
        center = first + rad * np.cross(axis, u)
        rvec = first - center
        for a0 in np.linspace(0, ang, max(3, math.ceil(ang / 0.22))):
            out.append(
                center + rvec * math.cos(a0) + np.cross(axis, rvec) * math.sin(a0)
            )
        radii.append(rad)
    out.append(v[-1])
    return out, radii


def whole_wire(q, plan):
    """A length-constrained conservative lay, not physical verification or a lead-cut instruction."""
    bx, by = q.pack["x"], q.pack["y"]
    sg = q.exit_sign

    def w(x, v, z):
        return [bx + x, by + sg * v, z]

    line = plan["centerlineXY"]

    def trial(t):
        # Two independent passages in the open-ended gate, one up to the form and one back to the carrier.
        gate = 18.65 if q.h["hand"] == "left" else 20.85
        ex = 2.4 if q.h["hand"] == "left" else -2.4
        path = [w(ex, 16, 1), w(ex, gate, 1), w(ex, gate, 7.75)]
        if q.h["hand"] == "left":
            v = 17 - t * 8
            path += [w(ex, v, 7.75), w(-ex, v, 7.75)]
            tail_z = 7.75
        else:
            r = 4.00 + t * 1.90
            near = 5.15 + t * 4.55
            far = 6.00 + t * 5.60
            theta = math.radians(123.0)
            xy = [
                (r * math.cos(a), near + r * math.sin(a))
                for a in np.linspace(theta, math.pi, 5)
            ]
            xy.extend(
                (r * math.cos(a), -far + r * math.sin(a))
                for a in np.linspace(math.pi, 2 * math.pi, 15)
            )
            xy.extend(
                (r * math.cos(a), near + r * math.sin(a))
                for a in np.linspace(0, math.pi - theta, 5)
            )
            path += [
                w(x, y, 7.75 + 1.65 * i / (len(xy) - 1)) for i, (x, y) in enumerate(xy)
            ]
            tail_z = 9.40
        path += [w(-ex, 18.65, tail_z), w(-ex, 18.65, 0.90)]
        path += [[x, y, 0.90] for x, y in line[1:-1]] + [[*line[-1], 2.45]]
        return fillet3(path)

    def length(pts):
        return sum(float(np.linalg.norm(b - a)) for a, b in zip(pts, pts[1:]))

    lo, hi = 0.0, 1.0
    l0 = length(trial(lo)[0])
    l1 = length(trial(hi)[0])
    if not l0 <= 105 <= l1:
        raise ValueError(
            f"{q.h['hand']}: 105-mm form cannot close the actual route ({l0:.2f}..{l1:.2f})"
        )
    for _ in range(28):
        mid = (lo + hi) / 2
        if length(trial(mid)[0]) < 105:
            lo = mid
        else:
            hi = mid
    path, radii = trial((lo + hi) / 2)
    xyz = [v.tolist() for v in path]
    # Conservative 3-D slab material: every segment has in-plane half-width 1.10 and Z allowance ±0.60.
    # Split long slopes into <=0.20-mm Z steps to avoid treating a diagonal as a tall solid block.
    pieces = []
    for idx, (a, b) in enumerate(zip(path, path[1:])):
        n = max(1, math.ceil(abs(b[2] - a[2]) / 0.18))
        for j in range(n):
            p = a + (b - a) * j / n
            r = a + (b - a) * (j + 1) / n
            pg = (
                LineString((p[:2], r[:2])).buffer(1.10, quad_segs=5)
                if np.linalg.norm(p[:2] - r[:2]) > 1e-8
                else disk(*p[:2], 1.1)
            )
            if idx == 0:
                # Flat wire emerges from the end face; its external volume begins there (not a spherical cap inside the cell).
                from shapely.geometry import box

                pg = pg.intersection(
                    box(
                        bx - 10,
                        q.end if sg > 0 else q.end - 20,
                        bx + 10,
                        q.end + 20 if sg > 0 else q.end,
                    )
                )
            pieces.append((min(p[2], r[2]) - 0.60, max(p[2], r[2]) + 0.60, pg))
    layers = []
    for i in range(
        math.floor(min(v[0] for v in pieces) / 0.25),
        math.ceil(max(v[1] for v in pieces) / 0.25),
    ):
        z = i * 0.25
        pg = join(*[p for l, h, p in pieces if min(h, z + 0.25) > max(l, z) + 1e-8])
        if not pg.is_empty:
            layers.append((z, z + 0.25, pg))
    info = {
        "coordinateFrame": "Canonical product geometry: +x right, +y palm, +z above PCB top; convert to CAD via (x,-y,z).",
        "centerlineXYZ_mm": [[round(float(c), 4) for c in p] for p in xyz],
        "centerlineLength_mm": round(length(path), 4),
        "roundJunctionMinRadius_mm": round(min(radii), 3),
        "drawingLimitConfirmed": False,
        "fittedCableValidated": False,
        "description": "Numerical 105.000-mm, unstretched same-length hypothesis including PH end rise, divider transit, and partial/one-turn storage; no cut to cell wires. Conservative 0.25-mm height bands with 2.20×1.20 lead allowance. Real 100-mm drawing vs 105-mm listing, end datums, acceptable radius, tolerance and mechanical strain are still open.",
    }
    return info, layers


def ribbon_step(info, halfwidth=1.1, halfheight=.60):
    """Oriented, faceted elliptical lead-pair reference for STEP; validation uses larger rectangular swept reservations."""
    from build123d import Wire, Solid, Color

    pts = np.asarray(info["centerlineXYZ_mm"])
    records = []
    last = None
    for i, p in enumerate(pts):
        axis = pts[min(len(pts) - 1, i + 1)] - pts[max(0, i - 1)]
        axis /= np.linalg.norm(axis)
        w = np.cross([0, 0, 1], axis)
        if np.linalg.norm(w) < 0.05 and last is not None:
            w = last - axis * (last @ axis)
        if np.linalg.norm(w) < 1e-6:
            w = np.array([1.0, 0.0, 0.0])
        w /= np.linalg.norm(w)
        if last is not None and w @ last < 0:
            w = -w
        last = w
        n = np.cross(axis, w)
        n /= np.linalg.norm(n)
        ring = [
            p + halfwidth * w * math.cos(a) + halfheight * n * math.sin(a)
            for a in np.arange(8) * math.pi / 4
        ]
        records.append(
            Wire.make_polygon(
                [(float(x), -float(y), float(z)) for x, y, z in ring], close=True
            )
        )
    shape = Solid.make_loft(records, ruled=True)
    if not shape.is_valid:
        raise ValueError("Invalid display-only cable loft")
    shape.label = "Uncut_105mm_battery_lead_reference"
    shape.color = Color(0.7, 0.34, 0.22)
    return shape


def layered_overlap(layers, material):
    return sum(
        max(0.0, min(u, y) - max(l, x)) * p.intersection(q).area
        for l, u, p in layers
        for x, y, q in material
        if min(u, y) > max(l, x) + 1e-7 and p.intersects(q)
    )


def analog_bands(h):
    """Four-conductor bundle (2.8 × 0.8 mm) along the canonical pad-edge route; no presumed mate/FFC connector."""
    if "sensorToDriver" not in h["wiring"]:
        return []
    p = np.asarray(h["wiring"]["sensorToDriver"]["points"])
    bins = {}
    for a, b in zip(p, p[1:]):
        count = max(1, math.ceil(np.linalg.norm(b - a) / 0.4))
        for j in range(count):
            u = a + (b - a) * j / count
            v = a + (b - a) * (j + 1) / count
            pg = LineString((u[:2], v[:2])).buffer(1.4, quad_segs=5)
            for i in range(
                math.floor((min(u[2], v[2]) - 0.4) / 0.20),
                math.ceil((max(u[2], v[2]) + 0.4) / 0.20),
            ):
                bins.setdefault(i, []).append(pg)
    return [(i * 0.2, (i + 1) * 0.2, join(*polys)) for i, polys in sorted(bins.items())]
