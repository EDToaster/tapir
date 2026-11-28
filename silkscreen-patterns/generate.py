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
