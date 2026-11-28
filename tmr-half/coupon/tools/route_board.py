#!/usr/bin/python3
"""Route the placed coupon with FreeRouting, then add ground fills.

  route_board.py dsn    export build/route/tmr-coupon.dsn from the placed board
  route_board.py ses    import routing/tmr-coupon.ses, restore class widths, fill GND, save the board

The .ses file under routing/ is the accepted copper. Re-importing it reproduces
the board without Java. Footprint records are copied back from the placed board
byte for byte, because the Specctra round trip may round pad coordinates.
"""
import json
import math
import re
import subprocess
import sys
import pcbnew as k
from design import ROOT, STEM, uid
from place_board import ORIGIN, W, H, RADIUS, ANTENNA, HOLES, FIDUCIALS, xy

PLACED = ROOT / "build" / (STEM + ".kicad_pcb")
WORK = ROOT / "build" / "route"
SESSION = ROOT / "routing" / (STEM + ".ses")
FINAL = ROOT / (STEM + ".kicad_pcb")
EDGE_INSET = 0.20
OUT2_GUIDE = [
    (133.825, 110.1, k.B_Cu), (133.825, 108.0, k.B_Cu),
    (133.825, 108.0, k.F_Cu), (136.0, 110.175, k.F_Cu),
    (136.0, 116.0, k.F_Cu), (134.35, 117.65, k.F_Cu),
    (134.35, 117.65, k.B_Cu), (133.8, 117.65, k.B_Cu), (133.5, 117.35, k.B_Cu),
]


def out2_guide(board):
    """Pre-route the trapped inner-row mux pin across the switch-hole field."""
    net = board.FindNet("OUT2")
    for a, b in zip(OUT2_GUIDE, OUT2_GUIDE[1:]):
        pa, pb = (k.VECTOR2I(k.FromMM(x), k.FromMM(y)) for x, y, _ in (a, b))
        if a[2] != b[2]:
            item = k.PCB_VIA(board); item.SetPosition(pa); item.SetWidth(k.FromMM(0.6))
            item.SetDrill(k.FromMM(0.30)); item.SetViaType(k.VIATYPE_THROUGH)
            item.SetLayerPair(k.F_Cu, k.B_Cu)
        else:
            item = k.PCB_TRACK(board); item.SetStart(pa); item.SetEnd(pb); item.SetLayer(a[2])
            item.SetWidth(k.FromMM(0.20))
        item.SetNet(net); board.Add(item)


def trim_ground_tracks(board):
    """Remove router ground segments wholly redundant with a continuous pour."""
    pours = {z.GetLayer(): z.GetFilledPolysList(z.GetLayer())
             for z in board.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()}
    count = 0
    for t in list(board.GetTracks()):
        if t.Type() == k.PCB_VIA_T or t.GetNetname() != "GND":
            continue
        a, b = t.GetStart(), t.GetEnd()
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        if not length:
            continue
        radius = (t.GetWidth() + k.FromMM(0.02)) / 2
        ux, uy = -dy * radius / length, dx * radius / length
        n = max(2, math.ceil(length/k.FromMM(0.15)))
        poly = pours[t.GetLayer()]
        if all(poly.Contains(k.VECTOR2I(round(a.x + dx*i/n + v*ux), round(a.y + dy*i/n + v*uy)))
               for i in range(n+1) for v in (-1, 0, 1)):
            board.Remove(t)
            count += 1
    print(f"  redundant ground trace segments removed: {count}")
    return count


def point_segment(x, y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = min(1, max(0, ((x - ax)*dx + (y - ay)*dy) / (dx*dx + dy*dy))) if dx or dy else 0
    return math.hypot(x - ax - t*dx, y - ay - t*dy)


def stitch(board, *, seed_only=False, seed=(), filled=False):
    """Ground both-sided copper near bypass pins and on a ~7 mm grid. No thin GND fanout."""
    gnd = board.FindNet("GND")
    rel = lambda p: (k.ToMM(p.x) - ORIGIN[0], k.ToMM(p.y) - ORIGIN[1])
    tracks, holes, pads, points, desired = [], [], [], [], []
    for t in board.GetTracks():
        if t.Type() == k.PCB_VIA_T:
            x, y = rel(t.GetPosition())
            holes.append((x, y, k.ToMM(t.GetDrillValue()) / 2))
            if t.GetNetname() == "GND":
                points.append((x, y))
            else:
                tracks.append((x, y, x, y, k.ToMM(t.GetWidth(k.F_Cu)) / 2))
        elif t.GetNetname() != "GND":
            tracks.append((*rel(t.GetStart()), *rel(t.GetEnd()), k.ToMM(t.GetWidth()) / 2))
    for f in board.GetFootprints():
        ref = f.GetReference()
        for p in f.Pads():
            x, y = rel(p.GetPosition())
            drill = k.ToMM(p.GetDrillSizeX())
            if drill:
                holes.append((x, y, drill / 2))
            if p.GetAttribute() == k.PAD_ATTRIB_NPTH:
                continue
            box = p.GetBoundingBox()
            pads.append((*rel(box.GetOrigin()), *rel(box.GetEnd())))
            if p.GetNetname() == "GND" and ref.startswith(("U", "C", "R", "J", "S", "D")) and not drill:
                desired.append((ref, p.GetNumber(), x, y))

    def boxdist(x, y, x1, y1, x2, y2):
        return math.hypot(max(x1 - x, 0, x - x2), max(y1 - y, 0, y - y2))

    def legal(x, y, compact=False):
        if not (0.7 < x < W - 0.7 and 0.7 < y < H - 0.7):
            return False
        if any(math.hypot(x - a, y - b) < 2.9 for a, b in HOLES):
            return False
        if boxdist(x, y, *ANTENNA[0], *ANTENNA[2]) < 0.45:
            return False
        if any(math.hypot(x-a, y-b) < r + (0.46 if compact else 0.67) for a, b, r in holes):
            return False
        if any(math.hypot(x-a, y-b) < (0.62 if compact else 0.82) for a, b in points):
            return False
        if any(boxdist(x, y, *p) < (0.505 if compact else 0.53) for p in pads):
            return False
        return all(point_segment(x, y, *t[:4]) >= t[4] + (0.505 if compact else 0.53) for t in tracks)

    def place(x, y):
        via = k.PCB_VIA(board); via.SetPosition(xy(x, y)); via.SetWidth(k.FromMM(0.6))
        via.SetDrill(k.FromMM(0.30)); via.SetViaType(k.VIATYPE_THROUGH); via.SetLayerPair(k.F_Cu, k.B_Cu)
        via.SetNet(gnd); via.SetUuid(k.KIID(uid(f"ground/stitch/{x}/{y}"))); board.Add(via)
        points.append((x, y))
        holes.append((x, y, 0.15))

    def add(cx, cy, distance):
        offsets = sorted((math.hypot(i, j), i, j) for i in range(-10, 11) for j in range(-10, 11))
        for d, i, j in offsets:
            if d * 0.15 > distance:
                break
            x, y = round(cx + i * 0.15, 4), round(cy + j * 0.15, 4)
            if not legal(x, y):
                continue
            place(x, y)
            return True
        return False

    if filled:
        pours = {z.GetLayer(): z.GetFilledPolysList(z.GetLayer())
                 for z in board.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()}
        before = len(points)
        for layer, poly in pours.items():
            other = pours[k.B_Cu if layer == k.F_Cu else k.F_Cu]
            for i in range(poly.OutlineCount()):
                count = sum(poly.Contains(xy(x, y), i) and other.Contains(xy(x, y)) for x, y in points)
                if count >= 2:
                    continue
                bounds = k.SHAPE_POLY_SET(poly.Polygon(i)).BBox()
                a, b = rel(bounds.GetOrigin()), rel(bounds.GetEnd())
                candidates = []
                for ix in range(math.ceil(a[0]*5), math.floor(b[0]*5)+1):
                    for iy in range(math.ceil(a[1]*5), math.floor(b[1]*5)+1):
                        x, y = ix/5, iy/5
                        q = xy(x, y)
                        if poly.Contains(q, i) and other.Contains(q) and legal(x, y):
                            candidates.append((x, y))
                while candidates and count < 2:
                    x, y = max(candidates, key=lambda p: min(math.dist(p, r) for r in points))
                    place(x, y)
                    count += 1
                    candidates = [p for p in candidates if legal(*p)]
                # Try a tighter grid at DRC clearance for very small regions.
                if count < 2:
                    for ix in range(math.ceil(a[0]*40), math.floor(b[0]*40)+1):
                        for iy in range(math.ceil(a[1]*40), math.floor(b[1]*40)+1):
                            x, y = ix/40, iy/40
                            q = xy(x, y)
                            if poly.Contains(q, i) and other.Contains(q) and legal(x, y, compact=True):
                                place(x, y)
                                count += 1
                                if count >= 2:
                                    break
                        if count >= 2:
                            break
        print(f"  additional ground stitching into split pours: {len(points)-before}")
        return len(points) - before

    for x, y in seed:
        place(x, y)
    critical = {(f"U{i}", "3") for i in range(1, 7)} | {("U7", "12"), ("U8", "12")}
    critical |= {(f"C{i}", "2") for i in range(1, 10)}
    for ref, p, x, y in sorted(desired):
        if seed_only and (ref, p) not in critical:
            continue
        if not any(math.hypot(x-a, y-b) <= 1.5 for a, b in points):
            if not add(x, y, 1.5):
                print(f"  ground via: no legal site within 1.5 mm of {ref}.{p}")
    if not seed_only:
        for x in range(5, 90, 8):
            for y in range(5, 48, 8):
                if not any(math.hypot(x-a, y-b) <= 3.0 for a, b in points):
                    add(x, y, 1.5)
        print(f"  ground stitching: {len(points)} vias")
    return points


def retain_placement(source, routed):
    pattern = re.compile(r'^\t\(footprint\b.*?^\t\)$', re.MULTILINE | re.DOTALL)
    ref = re.compile(r'\(property "Reference" "([^"]+)"')
    original = {ref.search(m[0])[1]: m[0] for m in pattern.finditer(source.read_text())}
    seen = set()

    def replace(m):
        key = ref.search(m[0])[1]
        if key in seen:
            raise ValueError("Duplicate footprint in routed output: " + key)
        seen.add(key)
        return original[key]
    data = pattern.sub(replace, routed.read_text())
    if not seen or seen != set(original):
        raise ValueError("Placed and routed footprint sets differ")
    routed.write_text(data)


def export_dsn(*, route_ground=False, guide=False):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / (STEM + ".ses")).unlink(missing_ok=True)
    board = k.LoadBoard(str(PLACED)); dsn = WORK / (STEM + ".dsn")
    if guide:
        out2_guide(board)
    if not k.ExportSpecctraDSN(board, str(dsn)):
        sys.exit("DSN export failed")
    # The router keeps its 0.20 mm clearance from the outline it is given, while the design rule is
    # 0.30 mm from the real edge. Hand it an outline pulled in by EDGE_INSET so it has margin.
    d, r = EDGE_INSET, RADIUS - EDGE_INSET; pts = []
    for cx, cy, a0 in ((W - d - r, d + r, -90), (W - d - r, H - d - r, 0), (d + r, H - d - r, 90), (d + r, d + r, 180)):
        for i in range(9):
            a = math.radians(a0 + i * 11.25)
            pts.append((ORIGIN[0] + cx + r * math.cos(a), ORIGIN[1] + cy + r * math.sin(a)))
    pts.append(pts[0])
    path = "(path pcb 0  " + "  ".join(f"{round(x * 1000)} {round(-y * 1000)}" for x, y in pts) + ")"
    text, count = re.subn(r"\(boundary\s*\(path pcb 0[^)]*\)", "(boundary\n      " + path, dsn.read_text())
    assert count == 1 and "(resolution um 10)" in text
    # KiCad's Specctra exporter does not include custom DRC rules. FreeRouting accepts named
    # class-to-class clearance pairs. Retain ordinary spacing to nearby ground pads.
    text = text.replace("(clearance 50 (type smd_smd))", "(clearance 200 (type smd_smd))")
    pairs = ''.join(f'    (class_class (classes "Analog,Default" "{b}") (rule (clearance 515)))\n'
                    for b in ("Control,Default", "Battery,Default"))
    text = text.replace("  )\n  (wiring", pairs + "  )\n  (wiring")
    if not route_ground:
        # Let the zone filler connect GND rather than replace the reference
        # plane with a tree. The disconnected pads remain copper obstacles.
        text, removed = re.subn(r"    \(net GND\n.*?^    \)\n", "", text, flags=re.S | re.M)
        assert removed == 1
        text = re.sub(r'(?<= )GND(?=\s)', '', text)
    # Reserve the most important bypass/stitch locations before routing obstructs them.
    seeds = stitch(board, seed_only=True)
    blocks = [(x, y, 0.32, ("F.Cu", "B.Cu")) for x, y in seeds]
    blocks += [(x, y, 0.86, ("B.Cu",)) for x, y in FIDUCIALS]
    keepouts = "".join(f'    (keepout "" (circle {layer} {round(2000*r)} '
                       f'{round(1000*(ORIGIN[0]+x))} {round(-1000*(ORIGIN[1]+y))}))\n'
                       for x, y, r, layers in blocks for layer in layers)
    text = text.replace("    (via ", keepouts + "    (via ", 1)
    dsn.write_text(text)
    print("wrote", WORK / (STEM + ".dsn"))


def import_ses():
    board = k.LoadBoard(str(PLACED))
    placements = {f.GetReference(): (tuple(f.GetPosition()), f.GetOrientationDegrees(), f.GetLayer())
                  for f in board.GetFootprints()}
    if not k.ImportSpecctraSES(board, str(SESSION)):
        sys.exit("SES import failed")
    for f in board.GetFootprints():
        pos, angle, layer = placements[f.GetReference()]
        if (abs((f.GetOrientationDegrees() - angle + 180) % 360 - 180) > 1e-6 or f.GetLayer() != layer
                or max(abs(a - b) for a, b in zip(pos, f.GetPosition())) > 100):
            sys.exit("Session moved footprint " + f.GetReference())
        f.SetPosition(k.VECTOR2I(*pos))
    if not list(board.GetTracks()):
        sys.exit("No copper in session")
    # FreeRouting necks traces at small pads. Restore each segment to its class width, then let KiCad's
    # own DRC name the few segments where the wider copper does not fit and give those back the
    # router's width (never below the 0.15 mm minimum track width). The design rules are not relaxed.
    project = json.loads(PLACED.with_suffix(".kicad_pro").read_text())
    widths = {c["name"]: k.FromMM(c["track_width"]) for c in project["net_settings"]["classes"]}
    floor = k.FromMM(project["board"]["design_settings"]["rules"]["min_track_width"])
    routed, seen = {}, set()
    for t in board.GetTracks():
        via = t.Type() == k.PCB_VIA_T
        spec = (t.GetNetname(), t.Type(), t.GetLayer(), tuple(t.GetStart()), tuple(t.GetEnd()),
                t.GetWidth(k.F_Cu) if via else t.GetWidth())
        ident = uid("copper/" + str(spec))
        if ident in seen:
            sys.exit("Duplicate track in session")
        seen.add(ident); t.SetUuid(k.KIID(ident))
        if not via:
            want = next((widths[n] for n in t.GetNet().GetNetClassName().split(",") if n in widths), widths["Default"])
            routed[ident] = max(t.GetWidth(), floor)
            t.SetWidth(max(t.GetWidth(), want))
    stitch(board, seed=stitch(k.LoadBoard(str(PLACED)), seed_only=True))
    # Exclude a pad-free sliver beside U8. Routed copper can cross the
    # rectangle; this restriction applies only to bottom zone fill.
    cut = k.ZONE(board); board.Add(cut)
    cut.SetIsRuleArea(True)
    bottom = k.LSET(); bottom.AddLayer(k.B_Cu); cut.SetLayerSet(bottom)
    cut.SetZoneName("Exclude pad-free ground sliver beside U8")
    cut.SetUuid(k.KIID(uid("zone/" + cut.GetZoneName())))
    cut.SetDoNotAllowTracks(False); cut.SetDoNotAllowVias(False)
    cut.SetDoNotAllowPads(False); cut.SetDoNotAllowFootprints(False)
    cut.SetDoNotAllowZoneFills(True)
    loop = cut.Outline(); loop.NewOutline()
    for x, y in ((67.22, 11.84), (67.84, 11.84), (67.84, 12.47), (67.22, 12.47)):
        loop.Append(xy(x, y))
    # Ground fill is the primary return path, not a thin-track tree.
    x0, y0 = ORIGIN
    for layer in (k.F_Cu, k.B_Cu):
        z = k.ZONE(board); board.Add(z); z.SetLayer(layer); z.SetNet(board.FindNet("GND"))
        z.SetZoneName("GND fill " + board.GetLayerName(layer)); z.SetUuid(k.KIID(uid("zone/" + z.GetZoneName())))
        # Bring the front reference closer to the mux/ADC routes without
        # changing copper-to-copper DRC or the bottom-side thermal clearance.
        z.SetLocalClearance(k.FromMM(0.20 if layer == k.F_Cu else 0.30))
        z.SetMinThickness(k.FromMM(0.20))
        z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(k.FromMM(0.25)); z.SetThermalReliefSpokeWidth(k.FromMM(0.20))
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline(); o.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            o.Append(k.VECTOR2I(k.FromMM(x0 + x), k.FromMM(y0 + y)))
    kept = 0
    for attempt in range(8):
        board.BuildConnectivity()
        if not k.ZONE_FILLER(board).Fill(board.Zones()):
            sys.exit("Zone fill failed")
        if attempt == 0:
            if trim_ground_tracks(board):
                board.BuildConnectivity()
                if not k.ZONE_FILLER(board).Fill(board.Zones()):
                    sys.exit("Zone refill after ground trace cleanup failed")
            if stitch(board, filled=True):
                board.BuildConnectivity()
                if not k.ZONE_FILLER(board).Fill(board.Zones()):
                    sys.exit("Zone refill after targeted stitching failed")
            if trim_ground_tracks(board):
                board.BuildConnectivity()
                if not k.ZONE_FILLER(board).Fill(board.Zones()):
                    sys.exit("Zone refill after final ground trace cleanup failed")
        if not k.SaveBoard(str(FINAL), board, True):
            sys.exit("Save failed")
        retain_placement(PLACED, FINAL)
        report = WORK / "fit-drc.json"
        subprocess.run(["kicad-cli", "pcb", "drc", "--all-track-errors", "--severity-error", "--format", "json",
                        "-o", str(report), str(FINAL)], check=True, stdout=subprocess.DEVNULL)
        tight = {i["uuid"] for v in json.loads(report.read_text())["violations"] if v["type"] == "clearance"
                 for i in v["items"]}
        change = [t for t in board.GetTracks() if t.Type() != k.PCB_VIA_T and t.m_Uuid.AsString() in tight
                  and t.GetWidth() > routed[t.m_Uuid.AsString()]]
        if not change:
            break
        for t in change:
            t.SetWidth(routed[t.m_Uuid.AsString()])
        kept += len(change)
    tracks = list(board.GetTracks())
    vias = sum(t.Type() == k.PCB_VIA_T for t in tracks)
    narrow = sum(1 for t in tracks if t.Type() != k.PCB_VIA_T and t.GetWidth() < next(
        (widths[n] for n in t.GetNet().GetNetClassName().split(",") if n in widths), widths["Default"]))
    print(f"{FINAL.name}: {len(tracks) - vias} segments, {vias} vias; {narrow} segments stay below class width "
          f"(router neck-downs kept where the full width does not fit)")


if __name__ == "__main__":
    if sys.argv[1] == "dsn":
        export_dsn(route_ground="--route-ground" in sys.argv[2:], guide="--out2-guide" in sys.argv[2:])
    else:
        {"ses": import_ses}[sys.argv[1]]()
