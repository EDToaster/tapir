#!/usr/bin/python3
"""Measure analog routing, ground return, and chip-pad copper on the filled board."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import pcbnew as k

from design import ANALOG, ROOT, STEM

CLEARANCE = 0.50
MAX_COUPLED = 3.0
MAX_BROADSIDE = 3.0
MIN_REFERENCE = 80.0
# Leave approximately three percentage points of regression margin on
# every baseline result, rounded down. The goal remains 80%; passing
# the regression floors makes no signal-integrity claim.
REFERENCE_FLOORS = {
    "OUT1": 64, "OUT2": 57, "OUT3": 82, "OUT4": 75, "OUT5": 97,
    "OUT6": 77, "MUXA": 44, "MUXB": 62, "AIN_A": 55, "AIN_B": 56,
}
AGGRESSOR_GROUPS = {
    "decoder_and_rail_control": ("S0", "S1", "S2", "S3", "MUX_EN_N", "PWR_A_N", "PWR_B_N"),
    "reset": ("RST",),
    "battery_connection_and_test": ("BAT_P", "BAT_F", "BAT_SW", "BAT_REV"),
    "switched_gate_supply_and_monitor": ("GATE_A", "GATE_B", "VSW_A", "VSW_B", "VS_A", "VS_B",
                                         "MON_A", "MON_B", "VCC"),
}
AGGRESSORS = tuple(net for group in AGGRESSOR_GROUPS.values() for net in group)
VICTIMS = (*ANALOG, "MON_A", "MON_B", "AIN_SPARE")
OWN_RAIL_PAD_ESCAPE = 1.5
# Existing coupling on frozen rev A copper. No permissive blanket rule.
# Tuple: exclusive same-layer and projected parallel length limits (mm),
# then inclusive victim / aggressor via counts within 0.50 mm.
# Reset and external VCC changes occur outside sampling; VS and MON
# exceptions must be evaluated in the physical rail settling test.
COUPLING_EXCEPTIONS = {
    "OUT3/VCC": (3.0, 5.40, 0, 0),
    "OUT6/VS_B": (1.25, 1.90, 0, 1),
    "MUXA/VS_A": (0.30, 4.60, 1, 0),
    "MUXA/VS_B": (0.30, 3.0, 1, 0),
    "MUXA/MON_A": (0.40, 1.60, 1, 0),
    "MUXB/RST": (3.0, 12.25, 0, 0),
    "AIN_SPARE/VSW_A": (1.15, 3.0, 1, 0),
    "AIN_SPARE/VSW_B": (0.25, 3.0, 1, 0),
}
MAX_REGIONS = {"F.Cu": 2, "B.Cu": 8}
MAX_GROUND_TRACK_MM = 337.0
MAX_STITCH_DISTANCE = 1.50
STEP = 0.05
LAYERS = (k.F_Cu, k.B_Cu)
MIN_ZONE_WIDTH = 0.20


def pt(v):
    return k.ToMM(v.x), k.ToMM(v.y)


def vec(p):
    return k.VECTOR2I(*(k.FromMM(q) for q in p))


def points(a, b, step=STEP):
    length = math.dist(a, b)
    n = max(1, math.ceil(length / step))
    for i in range(n):
        t = (i + 0.5)/n
        yield (a[0] + t*(b[0] - a[0]), a[1] + t*(b[1] - a[1])), length / n


class Segment:
    def __init__(self, track):
        self.layer = track.GetLayer()
        self.a, self.b = pt(track.GetStart()), pt(track.GetEnd())
        self.r = k.ToMM(track.GetWidth()) / 2
        self.length = math.dist(self.a, self.b)
        self.dx, self.dy = self.b[0]-self.a[0], self.b[1]-self.a[1]
        self.box = tuple(min(a, b) for a, b in zip(self.a, self.b)) + tuple(max(a, b) for a, b in zip(self.a, self.b))

    def dist(self, p):
        dx, dy = p[0]-self.a[0], p[1]-self.a[1]
        a = min(1, max(0, (dx*self.dx + dy*self.dy) / self.length**2)) if self.length else 0
        return math.hypot(dx - a*self.dx, dy - a*self.dy)

    def parallel(self, other):
        return bool(self.length and other.length and abs(self.dx*other.dx + self.dy*other.dy)
                    >= self.length*other.length*math.cos(math.radians(15)))

    def nearby(self, other, gap):
        slack = gap + self.r + other.r
        return all(self.box[i] <= other.box[i+2]+slack and other.box[i] <= self.box[i+2]+slack for i in range(2))

    def edge_gap(self, other):
        def side(a, b, p):
            return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])

        if (side(self.a, self.b, other.a)*side(self.a, self.b, other.b) < 0
                and side(other.a, other.b, self.a)*side(other.a, other.b, self.b) < 0):
            return -self.r-other.r
        return min(self.dist(other.a), self.dist(other.b), other.dist(self.a), other.dist(self.b))-self.r-other.r


class ViaDisk:
    def __init__(self, track):
        self.pos = pt(track.GetPosition())
        self.radii = {layer: k.ToMM(track.GetWidth(layer))/2 for layer in LAYERS if track.IsOnLayer(layer)}


def proximity(at, bt, av, bv, escapes):
    """Compare trace centrelines and via copper discs without assigning vias fictitious length."""
    nearest_trace, nearest_via = math.inf, math.inf
    same = opposite = exempt = 0.0
    a_hits, b_hits = set(), set()

    def local(p):
        return any(math.dist(p, e) <= OWN_RAIL_PAD_ESCAPE for e in escapes)

    for s in at:
        same_layer = [t for t in bt if t.layer == s.layer]
        nearest_trace = min(nearest_trace, *(s.edge_gap(t) for t in same_layer)) if same_layer else nearest_trace
        near = [t for t in bt if s.nearby(t, CLEARANCE)]
        coincident = [t for t in near if t.layer == s.layer]
        broadside = [t for t in near if t.layer != s.layer and s.parallel(t)]
        if coincident or broadside:
            for p, dl in points(s.a, s.b):
                if any(t.dist(p)-t.r-s.r < CLEARANCE for t in coincident):
                    if local(p):
                        exempt += dl
                    else:
                        same += dl
                if not local(p) and any(t.dist(p)-t.r-s.r < CLEARANCE for t in broadside):
                    opposite += dl
    for vias, segments, hits in ((av, bt, a_hits), (bv, at, b_hits)):
        for i, v in enumerate(vias):
            for s in segments:
                if s.layer not in v.radii:
                    continue
                gap = s.dist(v.pos)-s.r-v.radii[s.layer]
                nearest_via = min(nearest_via, gap)
                if gap < CLEARANCE and not local(v.pos):
                    hits.add(i)
    for i, v in enumerate(av):
        for j, w in enumerate(bv):
            common = v.radii.keys() & w.radii.keys()
            if not common:
                continue
            gap = math.dist(v.pos, w.pos)-max(v.radii[l]+w.radii[l] for l in common)
            nearest_via = min(nearest_via, gap)
            if gap < CLEARANCE and not (local(v.pos) and local(w.pos)):
                a_hits.add(i)
                b_hits.add(j)
    return dict(same_mm=round(same, 3), opposite_parallel_mm=round(opposite, 3),
                same_layer_own_supply_escape_mm=round(exempt, 3),
                min_same_layer_track_gap_mm=None if math.isinf(nearest_trace) else round(nearest_trace, 4),
                min_via_to_track_or_via_gap_mm=None if math.isinf(nearest_via) else round(nearest_via, 4),
                victim_vias_within_gap=len(a_hits), aggressor_vias_within_gap=len(b_hits))


def region_has(polygon, index, pos):
    return polygon.Contains(vec(pos), index)


def screen_zone_necks(poly):
    """First sampled width at which erosion splits a substantial copper region.

    Acute tips naturally approach zero width. This tests connecting necks,
    ignoring fragments under 0.02 mm² after erosion; it is not an etch model.
    """
    rings = [k.SHAPE_POLY_SET(poly.Polygon(i)) for i in range(poly.OutlineCount())]
    for ring in rings:
        ring.Unfracture()
    for width_um in range(50, 501, 5):
        for ring in rings:
            eroded = k.SHAPE_POLY_SET(ring)
            eroded.Deflate(width_um * 500, k.CORNER_STRATEGY_ROUND_ALL_CORNERS, k.FromMM(0.001))
            substantial = sum(k.SHAPE_POLY_SET(eroded.Polygon(i)).Area() >= 0.02e12
                              for i in range(eroded.OutlineCount()))
            if substantial > 1:
                return width_um / 1000
    return None


def calculate(board):
    fills, zone_minimums, vias, tracks, pads, net_vias = {}, {}, [], defaultdict(list), {}, defaultdict(list)
    for zone in board.Zones():
        if zone.GetNetname() == "GND" and not zone.GetIsRuleArea():
            for layer in LAYERS:
                if zone.IsOnLayer(layer):
                    poly = zone.GetFilledPolysList(layer)
                    fills[layer] = poly
                    zone_minimums[board.GetLayerName(layer)] = k.ToMM(zone.GetMinThickness())
    for t in board.GetTracks():
        if t.Type() == k.PCB_VIA_T:
            net_vias[t.GetNetname()].append(ViaDisk(t))
            if t.GetNetname() == "GND":
                vias.append(pt(t.GetPosition()))
        else:
            tracks[t.GetNetname()].append(Segment(t))
    for f in board.GetFootprints():
        pads[f.GetReference()] = (f.GetLayer(), list(f.Pads()))

    # Compare each mm of analog centreline once per aggressor net. Edge gap
    # is calculated with the two half-widths. On the other layer count only
    # parallel runs (<=15° apart) with a projected copper gap below 0.5 mm;
    # perpendicular crossings are not a broadside run.
    pairs, reference = {}, {}
    for net in ANALOG:
        length = sum(s.length for s in tracks[net])
        covered = 0.0
        for s in tracks[net]:
            layer = k.B_Cu if s.layer == k.F_Cu else k.F_Cu
            poly = fills[layer]
            covered += sum(dl for p, dl in points(s.a, s.b) if region_has(poly, -1, p))
        reference[net] = dict(length_mm=round(length, 3), opposite_ground_pct=round(100*covered/max(length, 1e-9), 1))
    for net in VICTIMS:
        for aggressor in AGGRESSORS:
            if net == aggressor:
                continue
            escapes = ()
            if net.startswith("OUT"):
                key = int(net.removeprefix("OUT"))
                if aggressor == ("VS_A" if key <= 3 else "VS_B"):
                    escapes = [pt(p.GetPosition()) for p in pads[f"U{key}"][1] if p.GetNumber() == "1"]
            pairs[f"{net}/{aggressor}"] = proximity(tracks[net], tracks[aggressor],
                                                  net_vias[net], net_vias[aggressor], escapes)
    diagnostic_pairs = [("MUXA", "MUXB")] + [("AIN_SPARE", n) for n in (*ANALOG, "MON_A", "MON_B")]
    diagnostic = {f"{a}/{b}": proximity(tracks[a], tracks[b], net_vias[a], net_vias[b], ())
                  for a, b in diagnostic_pairs}

    # Filled-zone polygons are separate regions when they do not touch on
    # their layer. A through-via counts as a stitch only if both sides meet
    # GND copper at its centre. PTH headers are intentionally not counted.
    pairs_by_via, two_sided = [], []
    for p in vias:
        regions = tuple(next((i for i in range(fills[layer].OutlineCount())
                              if region_has(fills[layer], i, p)), None) for layer in LAYERS)
        if None not in regions:
            pairs_by_via.append(regions)
            two_sided.append(p)
    ground = {}
    for axis, layer in enumerate(LAYERS):
        poly = fills[layer]
        regions = []
        for i in range(poly.OutlineCount()):
            regions.append(dict(area_mm2=round(k.SHAPE_POLY_SET(poly.Polygon(i)).Area() / 1e12, 3),
                                two_sided_vias=sum(p[axis] == i for p in pairs_by_via)))
        ground[board.GetLayerName(layer)] = sorted(regions, key=lambda p: p["area_mm2"], reverse=True)

    near_ground = {}
    critical = ({f"U{i}": "3" for i in range(1, 7)} | {"U7": "12", "U8": "12"}
                | {f"C{i}": "2" for i in range(1, 10)})
    for ref, pin in critical.items():
        layer, pp = pads[ref]
        pad = next(p for p in pp if p.GetNumber() == pin)
        if pad.GetNetname() != "GND":
            raise ValueError(f"Expected {ref}.{pin} on GND")
        pos = pt(pad.GetPosition())
        poly = fills[layer]
        # Pad centre is a void for a thermal; test actual pad shape against the
        # filled zone so a pad without effective local copper will be reported.
        shape = k.SHAPE_POLY_SET()
        pad.TransformShapeToPolygon(shape, layer, 0, k.FromMM(0.005))
        touch = k.SHAPE_POLY_SET(shape)
        touch.BooleanIntersection(poly)
        near_ground[f"{ref}.{pin}"] = dict(nearest_via_mm=round(min((math.dist(pos, v) for v in two_sided), default=999), 3),
                                          overlaps_local_pour=touch.Area() > 0)

    # Reflow screening metric: area of local pour plus this pad's own net
    # tracks lying in a centred 1 mm radius outside the land itself. This is
    # a geometry comparison, not a thermal model or a tombstone prediction.
    copper_balance = {}
    for ref, (layer, pp) in pads.items():
        if len(pp) != 2 or any(p.GetAttribute() != k.PAD_ATTRIB_SMD for p in pp):
            continue
        counts = []
        for pad in sorted(pp, key=lambda p: p.GetNumber()):
            x, y = pt(pad.GetPosition())
            own = k.SHAPE_POLY_SET()
            pad.TransformShapeToPolygon(own, layer, 0, k.FromMM(0.005))
            local = [s for s in tracks[pad.GetNetname()] if s.layer == layer and s.dist((x,y)) < 1+s.r]
            total = 0
            for i in range(-10, 11):
                for j in range(-10, 11):
                    if i*i + j*j > 100:
                        continue
                    p = (x+i/10, y+j/10)
                    if own.Contains(vec(p)):
                        continue
                    if (pad.GetNetname() == "GND" and region_has(fills[layer], -1, p)) or any(s.dist(p) < s.r for s in local):
                        total += 1
            counts.append(round(total * 0.01, 2))
        copper_balance[ref] = counts
    outside_pour = sum(dl for s in tracks["GND"] for p, dl in points(s.a, s.b)
                       if not region_has(fills[s.layer], -1, p))
    return dict(pairs=pairs, diagnostic_analog_pairs=diagnostic, reference=reference, ground_regions=ground,
                ground_vias=len(vias), two_sided_ground_vias=len(pairs_by_via),
                ground_track_mm=round(sum(s.length for s in tracks["GND"]), 3),
                ground_track_centreline_outside_pour_mm=round(outside_pour, 3),
                zone_minimum_configured_width_mm=zone_minimums,
                zone_erosion_first_neck_split_mm={board.GetLayerName(l): screen_zone_necks(p)
                                                for l, p in fills.items()},
                ground_pad_return=near_ground, two_pad_local_copper_mm2=copper_balance)


def violations(report):
    errors = []
    if any(w < MIN_ZONE_WIDTH for w in report["zone_minimum_configured_width_mm"].values()):
        errors.append("Ground zone configured minimum width below 0.20 mm")
    if any(w is not None and w < 0.15 for w in report["zone_erosion_first_neck_split_mm"].values()):
        errors.append("Ground zone neck screening found a bottleneck below 0.15 mm")
    for name, values in report["pairs"].items():
        limit = COUPLING_EXCEPTIONS.get(name, (MAX_COUPLED, MAX_BROADSIDE, 0, 0))
        if (values["same_mm"] >= limit[0] or values["opposite_parallel_mm"] >= limit[1]
                or values["victim_vias_within_gap"] > limit[2]
                or values["aggressor_vias_within_gap"] > limit[3]):
            errors.append(f"{name} spacing: {values}")
    for name, data in report["reference"].items():
        if not data["length_mm"] or data["opposite_ground_pct"] < REFERENCE_FLOORS[name]:
            errors.append(f"{name} ground reference: {data['opposite_ground_pct']}%")
    for layer, regions in report["ground_regions"].items():
        if not 1 <= len(regions) <= MAX_REGIONS[layer]:
            errors.append(f"{layer}: unexpected number of pour regions ({len(regions)})")
        weaker = sorted(r["area_mm2"] for r in regions if r["two_sided_vias"] < 2)
        if weaker:
            errors.append(f"{layer}: pour regions with fewer than two stitching vias ({weaker})")
    for name, data in report["ground_pad_return"].items():
        if data["nearest_via_mm"] > MAX_STITCH_DISTANCE or not data["overlaps_local_pour"]:
            errors.append(f"{name} ground return: {data}")
    if report["two_sided_ground_vias"] < 20:
        errors.append("Fewer than 20 vias tie the two GND layers")
    if report["ground_track_mm"] > MAX_GROUND_TRACK_MM:
        errors.append(f"Supplemental ground track budget exceeded ({report['ground_track_mm']} mm)")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=ROOT / (STEM + ".kicad_pcb"))
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "analog-layout.json")
    parser.add_argument("--report-only", action="store_true", help="baseline measurements only")
    args = parser.parse_args()
    report = calculate(k.LoadBoard(str(args.pcb)))
    errors = violations(report)
    report["gate"] = dict(passed=not errors, errors=errors, reference_target_pct=MIN_REFERENCE,
                          reference_regression_floors_pct=REFERENCE_FLOORS,
                          proximity_aggressor_groups=AGGRESSOR_GROUPS,
                          proximity_threshold_mm=CLEARANCE,
                          existing_coupling_exceptions=COUPLING_EXCEPTIONS,
                          own_sensor_supply_escape_radius_mm=OWN_RAIL_PAD_ESCAPE,
                          exclusions={"GND": "return reference; not a driven aggressor",
                                      "BAT_G": "Q3 gate pulled to GND, not externally driven",
                                      "pads": "fixed footprint pin geometry checked separately by DRC",
                                      "unconnected": "not driven",
                                      "AIN_SPARE": "unused analog node measured as victim; drive low when unused",
                                      "analog_to_analog": "MUXA/MUXB and spare neighbours reported separately"},
                          max_ground_regions=MAX_REGIONS, min_stitches_per_region=2)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Opposite-layer ground:", {n: d["opposite_ground_pct"] for n, d in report["reference"].items()})
    print("Ground:", {a: len(r) for a, r in report["ground_regions"].items()},
          f"regions; {report['two_sided_ground_vias']}/{report['ground_vias']} through vias contact both fills")
    for issue in errors:
        print("FAIL:", issue)
    return bool(errors) and not args.report_only


if __name__ == "__main__":
    raise SystemExit(main())
