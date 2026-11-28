"""Dynamic black/white silkscreen patterns for keyboard PCBs.

Each pattern varies across the board (flow, warp, density or scale change)
instead of repeating one tile. Geometry is in mm on a 400 x 250 mm canvas,
larger than any keyboard PCB (including full-size boards), so you can place,
scale and crop it freely. Strokes are >= 0.25 mm and filled features/gaps are >= 0.3 mm,
above common fab minimums (~0.15 mm line).

Usage: python3 gen2.py [outdir]
"""
import math, random, os, sys
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import LineString

W, H = 400.0, 250.0
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__))
SW = 0.3
PATTERNS = {}


def pattern(fn):
    PATTERNS[fn.__name__] = fn
    return fn


def svg_doc(body, stroke=SW, w=W, h=H, vb=None, extra_defs="", clip=None, bg=False):
    vb = vb or (0, 0, w, h)
    clip = clip or f'<rect x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}"/>'
    back = f'<rect x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}" fill="#fff"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb[2]}mm" height="{vb[3]}mm" '
            f'viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}">\n'
            f'<defs><clipPath id="c">{clip}</clipPath>{extra_defs}</defs>\n{back}'
            f'<g clip-path="url(#c)" fill="none" stroke="#000" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-linejoin="round">\n{body}\n</g></svg>\n')


def P(pts, closed=False, fill=None, sw=None):
    pts = list(pts)
    if len(pts) > 20:  # drop points that deviate < 0.02 mm from the simplified line
        pts = list(LineString(pts).simplify(0.02).coords)
    d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + (" Z" if closed else "")
    a = (f' fill="{fill}"' if fill else "") + (f' stroke-width="{sw}"' if sw else "")
    return f'<path d="{d}"{a}/>'


def noise_field(seed, sigma_mm, res=2.0, pad=20):
    """Smooth random field sampled at `res` samples/mm, normalized to [-1, 1]."""
    rng = np.random.default_rng(seed)
    z = gaussian_filter(rng.standard_normal((int((H + 2 * pad) * res), int((W + 2 * pad) * res))),
                        sigma_mm * res, mode="wrap")
    z = z / np.abs(z).max()

    def f(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        shape = np.broadcast(x, y).shape
        x, y = np.broadcast_to(x, shape).ravel(), np.broadcast_to(y, shape).ravel()
        v = map_coordinates(z, [(y + pad) * res, (x + pad) * res], order=1, mode="nearest")
        return v.reshape(shape)
    return f


def filled_contours(xs, ys, z, levels):
    """Return SVG path elements (evenodd fill) for regions where levels[0] <= z < levels[1]."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cs = plt.contourf(xs, ys, z, levels=levels)
    out = []
    for path in cs.get_paths():
        if len(path.vertices) == 0:
            continue
        d = []
        for poly in path.to_polygons(closed_only=True):
            if len(poly) < 3:
                continue
            # Douglas-Peucker at 0.02 mm: invisible at silkscreen resolution, ~5x smaller files
            poly = np.asarray(LineString(poly).simplify(0.02).coords)
            if len(poly) < 3:
                continue
            d.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in poly) + "Z")
        if d:
            out.append(f'<path d="{"".join(d)}" fill="#000" fill-rule="evenodd" stroke="none"/>')
    plt.close("all")
    return out


# 1. Op-art ribbons: stacked bands that swell and pinch around two "lenses" ---
@pattern
def op_art_ribbons():
    lenses = [(W * 0.28, H * 0.42, 62.0, 30.0), (W * 0.7, H * 0.6, 75.0, -36.0)]
    xs = np.linspace(-2, W + 2, 1400)

    def disp(y):
        d = np.zeros_like(xs) + 4 * np.sin(xs / W * 2 * math.pi * 1.5 + y / 30)
        for cx, cy, r, a in lenses:
            g = np.exp(-(((xs - cx) / r) ** 2 + ((y - cy) / (r * 0.9)) ** 2))
            d += a * g
        return d

    pitch, out = 2.6, []
    ys = np.arange(-30, H + 30, pitch)
    for i in range(0, len(ys) - 1, 2):
        y0, y1 = ys[i], ys[i + 1]
        top = y0 + disp(y0)
        # thickness modulated by distance to lens centers: thick far away, thin inside
        mod = np.ones_like(xs)
        for cx, cy, r, _ in lenses:
            mod -= 0.6 * np.exp(-(((xs - cx) / r) ** 2 + ((y0 - cy) / r) ** 2))
        bot = top + np.maximum(0.35, (y1 - y0 + 0.4) * mod)
        pts = list(zip(xs, top)) + list(zip(xs[::-1], bot[::-1]))
        out.append(P(pts, True, fill="#000", sw=0.01))
    return out, 0.01


# 2. Flow field: evenly spaced streamlines over a curl-noise vector field ------
@pattern
def flow_field():
    n1 = noise_field(21, 38)
    res = 2.0
    gx = np.arange(-2, W + 2, 1 / res); gy = np.arange(-2, H + 2, 1 / res)
    GX, GY = np.meshgrid(gx, gy)
    Z = n1(GX, GY)
    # curl of scalar noise -> divergence-free swirls
    VX = np.gradient(Z, axis=0); VY = -np.gradient(Z, axis=1)
    M = np.hypot(VX, VY) + 1e-12
    VX, VY = (VX / M).tolist(), (VY / M).tolist()
    nyv, nxv = len(gy), len(gx)

    def vel(x, y):
        i = min(nyv - 1, max(0, int(round((y + 2) * res))))
        j = min(nxv - 1, max(0, int(round((x + 2) * res))))
        return VX[i][j], VY[i][j]

    dsep, dtest, step = 1.6, 0.75, 0.4
    cell = dsep
    grid = {}

    def ok(x, y, d, own=None):
        if not (-1 < x < W + 1 and -1 < y < H + 1):
            return False
        gx, gy = int(x // cell), int(y // cell)
        for i in range(gx - 1, gx + 2):
            for j in range(gy - 1, gy + 2):
                for (px, py, lid) in grid.get((i, j), ()):
                    if lid == own:
                        continue
                    if (px - x) ** 2 + (py - y) ** 2 < d * d:
                        return False
        return True

    lines = []
    rnd = random.Random(4)
    seeds = [(rnd.uniform(0, W), rnd.uniform(0, H)) for _ in range(16000)]
    for lid, (sx, sy) in enumerate(seeds):
        if not ok(sx, sy, dsep):
            continue
        line = [(sx, sy)]
        for sgn in (1, -1):
            x, y = sx, sy
            pts = []
            for _ in range(1500):
                vx, vy = vel(x, y)
                nx, ny = x + sgn * vx * step, y + sgn * vy * step
                if not ok(nx, ny, dtest):
                    break
                # avoid self-tightening loops
                if len(pts) > 30 and math.hypot(nx - sx, ny - sy) < dtest:
                    break
                pts.append((nx, ny)); x, y = nx, ny
            line = (pts[::-1] + line) if sgn == -1 else (line + pts)
        if len(line) < 12:
            continue
        for (x, y) in line:
            grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y, lid))
        lines.append(line)
    return [P(l) for l in lines], 0.3


# 3. Quadtree Truchet: tiles subdivide toward two attractors, arcs scale down ---
@pattern
def quadtree_truchet():
    rnd = random.Random(9)
    attract = [(W * 0.22, H * 0.7), (W * 0.8, H * 0.25)]
    out = []

    def density(x, y):
        return max(math.exp(-((x - ax) ** 2 + (y - ay) ** 2) / (2 * 70 ** 2)) for ax, ay in attract)

    def tile(x, y, s):
        cx, cy = x + s / 2, y + s / 2
        if s > 7 and (s > 26 or rnd.random() < density(cx, cy) * 1.15 + 0.08):
            h = s / 2
            for dx in (0, h):
                for dy in (0, h):
                    tile(x + dx, y + dy, h)
            return
        n = 3 if s >= 20 else (2 if s >= 10 else 1)
        sw = max(0.3, min(1.4, s * 0.06))
        flip = rnd.random() < 0.5
        for k in range(1, n + 1):
            rr = s * k / (n + 1) if n > 1 else s / 2
            if flip:   # arcs around top-left and bottom-right corners
                arcs = [f"M{x+rr},{y} A{rr},{rr} 0 0 1 {x},{y+rr}",
                        f"M{x+s-rr},{y+s} A{rr},{rr} 0 0 1 {x+s},{y+s-rr}"]
            else:      # arcs around top-right and bottom-left corners
                arcs = [f"M{x+s-rr},{y} A{rr},{rr} 0 0 0 {x+s},{y+rr}",
                        f"M{x+rr},{y+s} A{rr},{rr} 0 0 0 {x},{y+s-rr}"]
            out.extend(f'<path d="{a}" stroke-width="{sw:.2f}"/>' for a in arcs)

    S = 52.0
    for i in range(int(W / S) + 1):
        for j in range(int(H / S) + 1):
            tile(i * S, j * S, S)
    return out, 0.3


# 4. Reaction-diffusion: Gray-Scott with feed/kill swept across the board -----
@pattern
def reaction_diffusion():
    res = 2.0  # cells per mm
    nx, ny = int(W * res), int(H * res)
    U = np.ones((ny, nx)); V = np.zeros((ny, nx))
    rng = np.random.default_rng(1)
    for _ in range(120):
        cx, cy = rng.integers(5, nx - 5), rng.integers(5, ny - 5)
        V[cy - 3:cy + 3, cx - 3:cx + 3] = 0.5; U[cy - 3:cy + 3, cx - 3:cx + 3] = 0.25
    V += 0.02 * rng.random((ny, nx))
    t = np.linspace(0, 0.9, nx)[None, :].repeat(ny, 0)
    # spots (left) -> worms -> labyrinth (right)
    F = 0.030 + 0.012 * t
    K = 0.062 - 0.0035 * t
    Du, Dv = 0.16, 0.08

    def lap(Z):
        return (np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z)
    for _ in range(14000):
        uvv = U * V * V
        U += Du * lap(U) - uvv + F * (1 - U)
        V += Dv * lap(V) + uvv - (F + K) * V
    xs = np.linspace(0, W, nx); ys = np.linspace(0, H, ny)
    z = gaussian_filter(V, 0.8)
    return filled_contours(xs, ys, z, [0.2, 10]), 0.01


# 5. Vortex grid: square lattice pinched and twisted by three wells ----------
@pattern
def vortex_grid():
    # each well pinches radius by up to 70% and twists by up to `tw` radians;
    # both are monotonic in r, so lines never cross or merge
    wells = [(W * 0.28, H * 0.4, 38.0, 2.2), (W * 0.6, H * 0.64, 52.0, -2.8), (W * 0.85, H * 0.27, 28.0, 1.8)]

    def warp(x, y):
        for cx, cy, R, tw in wells:
            rx, ry = x - cx, y - cy
            r = np.hypot(rx, ry); th = np.arctan2(ry, rx)
            g = np.exp(-(r / R) ** 2)
            r2 = r * (1 - 0.7 * g); th2 = th + tw * g
            x, y = cx + r2 * np.cos(th2), cy + r2 * np.sin(th2)
        return x, y

    out, pitch = [], 3.0
    t = np.linspace(-20, W + 20, 1400)
    for y in np.arange(-20, H + 20, pitch):
        X, Y = warp(t, np.full_like(t, y)); out.append(P(zip(X, Y)))
    t = np.linspace(-20, H + 20, 900)
    for x in np.arange(-20, W + 20, pitch):
        X, Y = warp(np.full_like(t, x), t); out.append(P(zip(X, Y)))
    return out, 0.25


# 6. Vasarely bulge: checkerboard inflated by two spheres --------------------
@pattern
def vasarely_bulge():
    spheres = [(W * 0.36, H * 0.5, 55.0, 1.25), (W * 0.76, H * 0.42, 36.0, 1.0)]

    def warp(x, y):
        for cx, cy, R, k in spheres:
            rx, ry = x - cx, y - cy
            u = (rx * rx + ry * ry) / (R * R)
            f = 1 + k * np.exp(-u)   # monotonic radial expansion for k < 2.2
            x, y = cx + rx * f, cy + ry * f
        return x, y

    s_ = 6.5
    out = []
    n = 10  # samples per edge so cells curve
    lin = np.linspace(0, 1, n, endpoint=False)
    for i in range(int(-60 / s_), int((W + 60) / s_)):
        for j in range(int(-60 / s_), int((H + 60) / s_)):
            if (i + j) % 2:
                continue
            x0, y0 = i * s_, j * s_
            ex = np.concatenate([x0 + lin * s_, np.full(n, x0 + s_), x0 + s_ - lin * s_, np.full(n, x0)])
            ey = np.concatenate([np.full(n, y0), y0 + lin * s_, np.full(n, y0 + s_), y0 + s_ - lin * s_])
            X, Y = warp(ex, ey)
            if X.max() < -5 or X.min() > W + 5 or Y.max() < -5 or Y.min() > H + 5:
                continue
            out.append(P(zip(X, Y), True, fill="#000", sw=0.01))
    return out, 0.01


# 7. Phyllotaxis: golden-angle dots that grow outward from an off-centre focus
@pattern
def phyllotaxis():
    out = []
    golden = math.pi * (3 - math.sqrt(5))
    cx, cy = W * 0.62, H * 0.5
    c = 2.6
    n = 0
    while True:
        r = c * math.sqrt(n)
        if r > 480: break
        a = n * golden
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        n += 1
        if not (-3 < x < W + 3 and -3 < y < H + 3):
            continue
        # concentric ripples of dot size, ripple wavelength stretches outward
        ripple = 0.5 + 0.5 * math.sin(2 * math.pi * math.sqrt(r) / 1.9)
        rad = 0.2 + 0.78 * ripple
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rad:.3f}" fill="#000" stroke="none"/>')
    return out, 0.3


# 8. Hex morph: hex cells change from dots -> rings -> solid hexes, rotating --
@pattern
def hex_morph():
    out, r = [], 4.2
    dx, dy = r * math.sqrt(3), r * 1.5
    n2 = noise_field(5, 50)
    for j in range(int(H / dy) + 3):
        for i in range(int(W / dx) + 3):
            cx = i * dx + (dx / 2 if j % 2 else 0); cy = j * dy
            t = min(1, max(0, cx / W + 0.25 * float(n2(cx, cy))))
            rot = math.radians(30 * t)
            # outer hex grows; a hole opens then closes again -> dot, ring, solid
            if t < 0.3:
                outer = r * (0.14 + 0.36 * t / 0.3)
                hole = 0.0
            else:
                u = (t - 0.3) / 0.7
                outer = r * (0.5 + 0.4 * u)
                hole = outer * 0.82 * math.sin(math.pi * min(1, u * 1.15))
            hexp = lambda rad: [(cx + rad * math.cos(rot + k * math.pi / 3),
                                 cy + rad * math.sin(rot + k * math.pi / 3)) for k in range(6)]
            d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in hexp(outer)) + "Z"
            if hole > 0.3 and (outer - hole) * 0.866 > 0.3:
                d += "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in hexp(hole)) + "Z"
            out.append(f'<path d="{d}" fill="#000" fill-rule="evenodd" stroke="none"/>')
    return out, 0.3


# 9. Marble bands: domain-warped stripes, alternating fill -------------------
@pattern
def marble_bands():
    res = 3.0
    xs = np.linspace(0, W, int(W * res)); ys = np.linspace(0, H, int(H * res))
    X, Y = np.meshgrid(xs, ys)
    a, b = noise_field(31, 34), noise_field(32, 34)
    c = noise_field(33, 14)
    wx = 45 * a(X, Y) + 8 * c(X, Y); wy = 45 * b(X, Y)
    phase = (X + wx) * 0.42 + (Y + wy) * 0.2
    z = np.sin(phase)
    # band duty cycle changes across the board: thin lines -> fat bands
    duty = np.linspace(0.85, -0.2, len(xs))[None, :]
    return filled_contours(xs, ys, z - duty, [0, 10]), 0.01


# 10. Circle packing: packed discs, filled with rings/solids/dots by size ----
@pattern
def circle_pack():
    rnd = random.Random(12)
    circles = []
    cell = 6.0; grid = {}

    def fits(x, y, r):
        gx, gy = int(x // cell), int(y // cell)
        rng = int((r + 37) // cell) + 1  # 37 = largest possible radius + gap
        for i in range(gx - rng, gx + rng + 1):
            for j in range(gy - rng, gy + rng + 1):
                for (px, py, pr) in grid.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < (pr + r + 0.6) ** 2:
                        return False
        return True

    for target in [30, 21, 15, 10, 7, 4.8, 3.3, 2.2, 1.5, 1.0, 0.7]:
        tries = int(W * H / (target * target) * 3)
        for _ in range(tries):
            x, y = rnd.uniform(-5, W + 5), rnd.uniform(-5, H + 5)
            r = target * rnd.uniform(0.8, 1.2)
            if fits(x, y, r):
                circles.append((x, y, r))
                grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y, r))
    out = []
    for x, y, r in circles:
        if r > 5:
            k = 0.0
            rr = r
            while rr > 0.6:
                out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rr:.2f}"/>')
                rr -= 1.6
        elif r > 2.5:
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"/>')
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r*0.45:.2f}" fill="#000" stroke="none"/>')
        else:
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#000" stroke="none"/>')
    return out, 0.3


# ---------------------------------------------------------------------------
# Helpers for the second set
# ---------------------------------------------------------------------------
IRES = 5.0  # samples per mm for implicit (raster -> contour) patterns


def grid(res=IRES, pad=0.0):
    xs = np.linspace(-pad, W + pad, int((W + 2 * pad) * res))
    ys = np.linspace(-pad, H + pad, int((H + 2 * pad) * res))
    X, Y = np.meshgrid(xs, ys)
    return xs, ys, X, Y


def implicit(xs, ys, field):
    """Ink where `field` > 0. `field` should be roughly a signed distance in mm."""
    return filled_contours(xs, ys, field, [0, max(1e3, float(np.nanmax(field)) + 1)])


def poisson(radius_fn, seed, k=24, bounds=(-4, -4, W + 4, H + 4)):
    """Variable-radius Poisson-disk sampling (Bridson dart throwing)."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = bounds
    rmin = 0.6
    cell = rmin / math.sqrt(2)
    gw = int((x1 - x0) / cell) + 1
    gridd = {}
    pts, active = [], []

    def ok(x, y, r):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        n = int(r / cell) + 2
        gx, gy = int((x - x0) / cell), int((y - y0) / cell)
        for i in range(gx - n, gx + n + 1):
            for j in range(gy - n, gy + n + 1):
                q = gridd.get((i, j))
                if q is not None:
                    px, py, pr = q
                    if (px - x) ** 2 + (py - y) ** 2 < max(r, pr) ** 2:
                        return False
        return True

    def add(x, y, r):
        gridd[(int((x - x0) / cell), int((y - y0) / cell))] = (x, y, r)
        pts.append((x, y, r)); active.append(len(pts) - 1)

    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    add(x, y, radius_fn(x, y))
    while active:
        idx = active[rnd.randrange(len(active))]
        px, py, pr = pts[idx]
        for _ in range(k):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(pr, 2 * pr)
            nx, ny = px + d * math.cos(a), py + d * math.sin(a)
            if x0 <= nx <= x1 and y0 <= ny <= y1:
                r = radius_fn(nx, ny)
                if ok(nx, ny, r):
                    add(nx, ny, r)
                    break
        else:
            active.remove(idx)
    return pts


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# 11. Ridgelines: stacked profiles with hidden-line removal ------------------
@pattern
def ridgelines():
    n, n2 = noise_field(41, 5), noise_field(42, 28)
    xs = np.linspace(-5, W + 5, 1800)
    env = np.full_like(xs, np.inf)
    out, pitch = [], 2.6
    for y0 in np.arange(H + 45, -5, -pitch):          # front (bottom) to back
        band = np.exp(-((xs - W * 0.5) / (W * 0.24)) ** 4)
        bump = np.clip(n(xs, y0) * 1.6 + 0.35, 0, None) ** 2
        h = 34 * band * bump * (0.55 + 0.45 * n2(xs, y0)) + 1.2 * n(xs * 3, y0)
        sy = y0 - h
        vis = sy < env - 0.45
        run = []
        for x, yv, v in zip(xs, sy, vis):
            if v:
                run.append((x, yv))
            elif len(run) > 1:
                out.append(P(run)); run = []
            else:
                run = []
        if len(run) > 1:
            out.append(P(run))
        env = np.minimum(env, sy)
    return out, 0.35


# 12. Engraved spheres: line-width shading wrapped over shaded spheres -------
@pattern
def engraved_spheres():
    xs, ys, X, Y = grid()
    spheres = [(W * 0.3, H * 0.48, 62), (W * 0.62, H * 0.36, 40), (W * 0.78, H * 0.7, 52), (W * 0.1, H * 0.15, 26)]
    hmax = np.zeros_like(X); nx = np.zeros_like(X); ny = np.zeros_like(X); nz = np.ones_like(X)
    for cx, cy, R in spheres:
        dx, dy = (X - cx) / R, (Y - cy) / R
        d2 = dx * dx + dy * dy
        z = np.sqrt(np.clip(1 - d2, 0, None)) * R
        top = (d2 < 1) & (z > hmax)
        hmax = np.where(top, z, hmax)
        nx = np.where(top, dx, nx); ny = np.where(top, dy, ny); nz = np.where(top, z / R, nz)
    L = np.array([-0.55, -0.6, 0.58]); L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    bg = 0.42 + 0.12 * noise_field(43, 40)(X, Y)
    dark = np.where(hmax > 0, 1 - lam, bg)
    dark = np.where((hmax > 0) & (hmax < 4), 0.95, dark)      # outline rim
    dark = np.clip(gaussian_filter(dark, 1.0), 0.1, 0.9)
    p = 2.0
    phase = 2 * np.pi * (Y - 0.55 * hmax) / p
    field = np.cos(phase) - np.cos(np.pi * dark)
    return implicit(xs, ys, field), 0.01


# 13. Delaunay shatter: triangles densify and fill toward an impact point ----
@pattern
def delaunay_shatter():
    from scipy.spatial import Delaunay
    ix, iy = W * 0.62, H * 0.46
    rnd = random.Random(13)
    pts = poisson(lambda x, y: 1.6 + 11 * min(1, math.hypot(x - ix, y - iy) / 170) ** 1.3, 13)
    xy = np.array([(x, y) for x, y, _ in pts])
    tri = Delaunay(xy)
    nz = noise_field(44, 18)
    out = []
    for simp in tri.simplices:
        A, B, C = xy[simp]
        a, b, c = np.linalg.norm(B - C), np.linalg.norm(A - C), np.linalg.norm(A - B)
        per = a + b + c
        inc = (a * A + b * B + c * C) / per
        area = abs((B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])) / 2
        rin = 2 * area / per
        g = 0.3
        if rin < g + 0.4:
            continue
        k = (rin - g) / rin
        poly = [inc + (v - inc) * k for v in (A, B, C)]
        dist = math.hypot(inc[0] - ix, inc[1] - iy) / 170
        if rnd.random() < 0.9 - 0.8 * dist + 0.25 * float(nz(inc[0], inc[1])):
            out.append(P(poly, True, fill="#000", sw=0.01))
        else:
            out.append(P(poly, True))
    return out, 0.3


# 14. Lens Hilbert: one continuous space-filling curve under three lenses ----
@pattern
def lens_hilbert():
    order = 8
    n = 2 ** order

    def d2xy(d):
        x = y = 0; t = d; s = 1
        while s < n:
            rx = 1 & (t // 2); ry = 1 & (t ^ rx)
            if ry == 0:
                if rx == 1:
                    x, y = s - 1 - x, s - 1 - y
                x, y = y, x
            x += s * rx; y += s * ry
            t //= 4; s *= 2
        return x, y
    side = 420.0
    c = side / n
    pts = np.array([d2xy(d) for d in range(n * n)], float) * c + c / 2
    X = pts[:, 0] - (side - W) / 2; Y = pts[:, 1] - (side - H) / 2
    for cx, cy, R, k in [(W * 0.3, H * 0.45, 50, 1.2), (W * 0.7, H * 0.62, 38, 1.1), (W * 0.82, H * 0.2, 24, 0.9)]:
        rx, ry = X - cx, Y - cy
        f = 1 + k * np.exp(-(rx * rx + ry * ry) / (R * R))
        X, Y = cx + rx * f, cy + ry * f
    keep = (X > -10) & (X < W + 10) & (Y > -10) & (Y < H + 10)
    out, run = [], []
    for x, y, kp in zip(X, Y, keep):
        if kp:
            run.append((x, y))
        elif run:
            if len(run) > 1: out.append(P(run))
            run = []
    if len(run) > 1: out.append(P(run))
    return out, 0.32


# 15. Bipolar spiral checker: log-spiral checkerboard around two poles -------
@pattern
def spiral_checker():
    xs, ys, X, Y = grid()
    a, b = complex(W * 0.33, H * 0.5), complex(W * 0.7, H * 0.5)
    Z = X + 1j * Y
    w = np.log((Z - a) / (Z - b))
    u, v = w.real, w.imag
    n1, k1, n2, k2 = 9, 2.2, 3, 6.5   # two different log spirals
    s1 = np.sin(n1 * v + k1 * u); s2 = np.sin(n2 * v - k2 * u)
    field = s1 * s2
    # local cell size; fill the poles solid where cells get too small to print
    dzdw = np.abs((Z - a) * (Z - b) / (a - b))
    cell = dzdw * np.pi / max(math.hypot(n1, k1), math.hypot(n2, k2))
    field = field / (np.abs(np.gradient(field, axis=1)) * IRES + np.abs(np.gradient(field, axis=0)) * IRES + 1e-6)
    field = np.where(cell < 1.4, 1.0 + (1.4 - cell), field)
    return implicit(xs, ys, np.clip(field, -5, 5)), 0.01


# 16. Penrose inset: P2 Robinson triangles shrinking and swelling with noise -
@pattern
def penrose_inset():
    import cmath
    phi = (1 + 5 ** 0.5) / 2
    c0 = complex(W / 2, H / 2)
    tris = []
    for i in range(10):
        B = c0 + cmath.rect(250, (2 * i - 1) * math.pi / 10)
        C = c0 + cmath.rect(250, (2 * i + 1) * math.pi / 10)
        if i % 2 == 0:
            B, C = C, B
        tris.append((0, c0, B, C))
    for _ in range(8):
        res = []
        for col, A, B, C in tris:
            if col == 0:
                Pp = A + (B - A) / phi
                res += [(0, C, Pp, B), (1, Pp, C, A)]
            else:
                Q = B + (A - B) / phi; Rr = B + (C - B) / phi
                res += [(1, Rr, C, A), (1, Q, Rr, B), (0, Rr, Q, A)]
        tris = res
    nz = noise_field(46, 45)
    out = []
    for col, A, B, C in tris:
        g = (A + B + C) / 3
        if not (-8 < g.real < W + 8 and -8 < g.imag < H + 8):
            continue
        t = 0.5 + 0.5 * float(nz(g.real, g.imag)) * 1.4
        t = min(1, max(0, t))
        k = 0.4 + 0.38 * (t if col == 0 else 1 - t)
        poly = [(g + (p - g) * k) for p in (A, B, C)]
        out.append(P([(p.real, p.imag) for p in poly], True, fill="#000", sw=0.01))
    return out, 0.01


# 17. Field hatching: short strokes combed along a vector field --------------
@pattern
def field_hatching():
    n1, n2 = noise_field(47, 30), noise_field(48, 22)
    s = 2.6
    out = []
    dy = s * math.sqrt(3) / 2
    for j in range(int(H / dy) + 2):
        for i in range(int(W / s) + 2):
            x = i * s + (s / 2 if j % 2 else 0); y = j * dy
            e = 0.4
            gx = float(n1(x + e, y) - n1(x - e, y)); gy = float(n1(x, y + e) - n1(x, y - e))
            a = math.atan2(gx, -gy)                       # along the contour
            t = 0.5 + 0.5 * float(n2(x, y)) * 1.5
            t = min(1, max(0, t))
            L = s * (0.2 + 0.6 * t) / 2
            sw = 0.3 + 0.3 * t
            out.append(f'<path d="M{x - L*math.cos(a):.2f},{y - L*math.sin(a):.2f} L{x + L*math.cos(a):.2f},{y + L*math.sin(a):.2f}" stroke-width="{sw:.2f}"/>')
    return out, 0.3


# 18. Voronoi inset: organic cells whose gutters widen across the board -----
@pattern
def voronoi_inset():
    from shapely.geometry import MultiPoint, box
    from shapely.ops import voronoi_diagram
    nz = noise_field(49, 50)
    pts = poisson(lambda x, y: 3.2 + 4.0 * (0.5 + 0.5 * float(nz(x, y))), 18)
    mp = MultiPoint([(x, y) for x, y, _ in pts])
    bb = box(-6, -6, W + 6, H + 6)
    regions = voronoi_diagram(mp, envelope=bb)
    out = []
    for cell in regions.geoms:
        cell = cell.intersection(bb)
        if cell.is_empty:
            continue
        cx, cy = cell.centroid.x, cell.centroid.y
        t = min(1, max(0, cx / W * 0.8 + 0.15 + 0.25 * float(nz(cx + 300, cy))))
        g = 0.18 + t * 0.42 * math.sqrt(cell.area / math.pi)
        shp = cell.buffer(-g, join_style="round")
        if shp.is_empty or shp.area < 0.25:
            continue
        geoms = getattr(shp, "geoms", [shp])
        for gm in geoms:
            out.append(P(list(gm.exterior.coords), True, fill="#000", sw=0.01))
    return out, 0.01


# 19. Warped weave: over-under bands with varying width, gently warped ------
@pattern
def warped_weave():
    xs, ys, X, Y = grid()
    a, b, c = noise_field(51, 45), noise_field(52, 45), noise_field(53, 35)
    U = X + 9 * a(X, Y); V = Y + 9 * b(X, Y)
    s = 7.5
    i = np.floor(U / s); j = np.floor(V / s)
    du = np.abs(U - (i + 0.5) * s); dv = np.abs(V - (j + 0.5) * s)
    hw = 2.35 + 0.95 * c(X, Y)
    g, groove = 0.6, 0.3
    topH = ((i + j) % 2) == 0
    big = 1e3
    inkH = np.minimum.reduce([hw - dv, np.where(topH, big, du - hw - g), dv - groove])
    inkV = np.minimum.reduce([hw - du, np.where(topH, dv - hw - g, big), du - groove])
    return implicit(xs, ys, np.maximum(inkH, inkV)), 0.01


# 20. Metaball contours: iso-lines of merging point charges, solid cores ----
@pattern
def metaball_contours():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xs, ys, X, Y = grid(res=3.0)
    rnd = random.Random(20)
    cs_ = [(rnd.uniform(0.05, 0.95) * W, rnd.uniform(0.1, 0.9) * H, rnd.uniform(14, 38)) for _ in range(8)]
    F = sum(m / np.hypot(X - cx, Y - cy).clip(0.5) for cx, cy, m in cs_)
    fmax = float(np.quantile(F, 0.96))
    levels = np.geomspace(float(np.quantile(F, 0.005)), fmax, 64)
    cs = plt.contour(xs, ys, F, levels=levels)
    out = []
    for li, segs in enumerate(cs.allsegs):
        for seg in segs:
            if len(seg) < 3: continue
            w = 0.6 if li % 6 == 0 else 0.3
            out.append(f'<path d="M' + " L".join(f"{x:.2f},{y:.2f}" for x, y in seg) + f'" stroke-width="{w}"/>')
    plt.close("all")
    cores = filled_contours(xs, ys, F, [fmax * 1.12, F.max() + 1])
    return out + cores, 0.3


# 21. Interference rings: checkerboard of two ring families ------------------
@pattern
def interference_rings():
    xs, ys, X, Y = grid()
    r1 = np.hypot(X - W * 0.38, Y - H * 0.42); r2 = np.hypot(X - W * 0.6, Y - H * 0.6)
    p = 6.0
    f = np.sin(2 * np.pi * r1 / p) * np.sin(2 * np.pi * r2 / p)
    gy, gx = np.gradient(f)
    f = f / ((np.hypot(gx, gy) * IRES) + 1e-3)
    return implicit(xs, ys, np.clip(f, -5, 5)), 0.01


# 22. Seigaiha waves: overlapping wave scales, ring weight drifting ----------
@pattern
def seigaiha():
    xs, ys, X, Y = grid()
    R = 11.0; p = 2.6
    dyr = R / 2
    nz = noise_field(54, 45)
    duty = np.clip(0.2 + 0.45 * (X / W) + 0.18 * nz(X, Y), 0.18, 0.7)
    best_d = np.full_like(X, np.inf); covered = np.zeros_like(X, bool)
    j0 = np.floor(Y / dyr).astype(int)
    for dj in range(4, -3, -1):          # front rows (larger j) first
        j = j0 + dj
        cy = j * dyr
        off = np.where(j % 2 == 0, 0.0, R)
        cx = np.round((X - off) / (2 * R)) * 2 * R + off
        d = np.hypot(X - cx, Y - cy)
        new = (~covered) & (d < R)
        best_d = np.where(new, d, best_d); covered |= new
    c0 = R - 0.4 - p * duty / 2
    field = np.minimum(np.cos(2 * np.pi * (c0 - best_d) / p) - np.cos(np.pi * duty), (R - 0.4 - best_d))
    field = np.minimum(field, best_d - 1.2)  # no specks at scale centers
    field = np.where(covered, field, -1)
    return implicit(xs, ys, field), 0.01


# 23. Whirling squares: inscribed-square spirals, twist varies per cell -----
@pattern
def whirling_squares():
    nz = noise_field(55, 40)
    s = 18.0
    out = []
    for i in range(int(W / s) + 1):
        for j in range(int(H / s) + 1):
            cx, cy = i * s + s / 2, j * s + s / 2
            t = 0.5 + 0.5 * float(nz(cx, cy)) * 1.5
            alpha = math.radians(8 + 10 * min(1, max(0, t)))
            sign = 1 if (i + j) % 2 == 0 else -1
            hs = (s - 0.8) / 2
            corners = [(-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)]
            while hs > 2.0:
                out.append(P([(cx + x, cy + y) for x, y in corners], True))
                # next square: points a fraction along each edge
                f = math.tan(alpha) / (1 + math.tan(alpha))
                if sign < 0:
                    f = 1 - f
                corners = [(corners[q][0] + (corners[(q + 1) % 4][0] - corners[q][0]) * f,
                            corners[q][1] + (corners[(q + 1) % 4][1] - corners[q][1]) * f) for q in range(4)]
                hs = math.hypot(corners[0][0] - corners[1][0], corners[0][1] - corners[1][1]) / 2
    return out, 0.28


# 24. Sunburst bands: wobbling rays whose width pulses with radius ----------
@pattern
def sunburst_bands():
    xs, ys, X, Y = grid()
    cx, cy = W * 0.3, H * 0.58
    r = np.hypot(X - cx, Y - cy); th = np.arctan2(Y - cy, X - cx)
    n = 160
    ph = n * th + 2.2 * np.sin(r / 14)
    duty = 0.5 + 0.38 * np.cos(2 * np.pi * r / 38)
    f = np.cos(ph) - np.cos(np.pi * duty)
    arc = 2 * np.pi * r / n
    f = f * arc / np.pi                                    # ~ mm
    f = np.where(r < 34, -1, f)
    f = np.where(r < 14, 1, f)
    return implicit(xs, ys, f), 0.01


# 25. Stipple gradient: blue-noise dots with density from a noise field -----
@pattern
def stipple_gradient():
    nz = noise_field(56, 35)
    def rad(x, y):
        t = 0.5 + 0.5 * float(nz(x, y)) * 1.6
        t = min(1, max(0, t)) * 0.7 + 0.3 * min(1, max(0, x / W))
        return 1.25 + 3.8 * t
    pts = poisson(rad, 25)
    out = [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{0.48 - 0.16 * min(1, (r - 1.25) / 3.8):.2f}" fill="#000" stroke="none"/>'
           for x, y, r in pts]
    return out, 0.3


# 26. Cross-hatch shading: one to three hatch layers by tone ----------------
@pattern
def crosshatch_shading():
    xs, ys, X, Y = grid()
    tone = 0.5 + 0.5 * noise_field(57, 30)(X, Y) * 1.6
    tone = np.clip(tone * 0.75 + 0.25 * (1 - np.abs(Y / H - 0.5) * 2), 0, 1)
    p = 1.7
    fields = []
    for ang, t0 in ((45, 0.18), (-45, 0.45), (0, 0.72)):
        a = math.radians(ang)
        u = X * math.cos(a) + Y * math.sin(a)
        d = np.abs((u / p) % 1 - 0.5) * p
        hw = 0.16 + 0.2 * smoothstep(t0, t0 + 0.2, tone)
        fields.append(np.where(tone > t0, hw - d, -1))
    return implicit(xs, ys, np.maximum.reduce(fields)), 0.01


if __name__ == "__main__":
    import cairosvg
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    only = set(sys.argv[2:])
    for i, (name, fn) in enumerate(PATTERNS.items(), 1):
        if only and name not in only:
            continue
        body, stroke = fn()
        base = f"{i:02d}_{name}"
        s = svg_doc("\n".join(body), stroke)
        open(os.path.join(OUT, f"{base}.svg"), "w").write(s)
        sbg = svg_doc("\n".join(body), stroke, bg=True)
        cairosvg.svg2png(bytestring=sbg.encode(), write_to=os.path.join(OUT, "preview", f"{base}.png"),
                         output_width=2000)
        print("done", base, flush=True)
