#!/usr/bin/env python3
"""Read the plotted Gerber and drill files back with gerbonara 1.6.3 and compare them with the KiCad board.

Checks that every numbered pad is flashed at its position with its net, that every drill hit matches a
pad or via, and that the outline is closed and matches the board bounds.
"""
import json
import sys
from importlib.metadata import version
from pathlib import Path
from gerbonara import GerberFile, ExcellonFile
from gerbonara.graphic_objects import Arc, Flash, Line, Region
from shapely.geometry import Point
from cam_geometry import copper_shape, outline_polygon

ROOT = Path(__file__).resolve().parents[1]
STEM = "tmr-coupon"
plots = ROOT / "fab" / "gerbers"
native = json.loads((ROOT / "build" / "native.json").read_text())
out = {"parser": "gerbonara " + version("gerbonara"), "layers": {}, "drills": {}, "copper_lands": {}}
layers = {"F_Cu.gtl": "Copper,L1,Top", "B_Cu.gbl": "Copper,L2,Bot", "F_Mask.gts": "Soldermask,Top",
          "B_Mask.gbs": "Soldermask,Bot", "F_Silkscreen.gto": "Legend,Top", "B_Silkscreen.gbo": "Legend,Bot",
          "F_Paste.gtp": "Paste,Top", "B_Paste.gbp": "Paste,Bot", "Edge_Cuts.gm1": "Profile,NP"}
found = {f.name for f in plots.iterdir()}
want = {f"{STEM}-{s}" for s in layers} | {f"{STEM}-PTH.drl", f"{STEM}-NPTH.drl"}
if found != want:
    sys.exit(f"unexpected file set: {sorted(found ^ want)}")
profile = GerberFile.open(plots / f"{STEM}-Edge_Cuts.gm1")
outline = outline_polygon(profile)
# Both KiCad's bounding box and Gerber's include the drawn line width.
# All clearance measurements instead use its routed centreline.
plotted_bounds = [v for corner in profile.bounding_box("mm") for v in corner]
if max(abs(a-b) for a, b in zip(plotted_bounds, native["outline_bounds_mm"])) > 0.001:
    sys.exit(f"Gerber outline bounds {plotted_bounds} differ from KiCad {native['outline_bounds_mm']}")
out["copper_to_outline_centreline_mm"] = {}
for suffix, ident in layers.items():
    g = GerberFile.open(plots / f"{STEM}-{suffix}"); tag = ",".join(g.file_attrs[".FileFunction"])
    if tag != ident or (not g.objects and not suffix.startswith("F_Paste")):
        sys.exit(f"malformed or empty {suffix}: {tag}")
    out["layers"][suffix] = {"function": tag, "objects": len(g.objects)}
    key = suffix.split(".")[0]
    if key in native:
        got = sorted((o.attrs[".P"][0], o.attrs[".P"][1], round(o.x, 4), round(o.y, 4),
                      (o.attrs.get(".N") or ("",))[0])
                     for o in g.objects if isinstance(o, Flash) and len(o.attrs.get(".P", ())) >= 2
                     and (o.attrs[".P"][1] or o.attrs[".P"][0].startswith("FID")))
        expected = sorted((r, n, round(x, 4), round(y, 4), net) for r, n, x, y, net in native[key])
        if got != expected:
            sys.exit(f"{suffix}: pads differ. missing {sorted(set(expected) - set(got))[:8]} extra {sorted(set(got) - set(expected))[:8]}")
        out["copper_lands"][key] = len(expected)
    if key == "Edge_Cuts":
        (x1, y1), (x2, y2) = g.bounding_box("mm")
        out["outline_mm_including_line_width"] = [round(x2-x1, 3), round(y2-y1, 3)]
        out["outline_single_closed_loop"] = True

    if key in ("F_Cu", "B_Cu"):
        distances = {}
        for o in g.objects:
            if not o.polarity_dark:
                sys.exit(f"Unexpected clear copper primitive in {suffix}")
            if isinstance(o, Region):
                kind = "pour"
            elif isinstance(o, (Line, Arc)):
                kind = "track"
            elif isinstance(o, Flash):
                kind = "pad" if ".P" in o.attrs else "via"
            else:
                sys.exit(f"Unexpected copper geometry in {suffix}: {type(o).__name__}")
            shape = copper_shape(o)
            d = shape.distance(outline.boundary) if outline.covers(shape) else 0.0
            distances[kind] = min(d, distances.get(kind, float("inf")))
        # Arc flattening/plot grid error is below a micron. The 0.4 mm pour
        # inset is separate from the unchanged 0.30 mm project clearance.
        for kind, d in distances.items():
            if d + 0.001 < (0.40 if kind == "pour" else 0.30):
                sys.exit(f"{suffix}: {kind} copper to routed edge {d:.4f} mm")
        out["copper_to_outline_centreline_mm"][key] = {k: round(d, 4) for k, d in distances.items()}

    if key in ("B_Cu", "B_Mask"):
        fid = []
        fid_edge = {}
        for ref, _, x, y, _ in native["B_Cu"]:
            if not ref.startswith("FID"):
                continue
            flashes = [o for o in g.objects if isinstance(o, Flash) and abs(o.x-x) < 1e-6 and abs(o.y-y) < 1e-6]
            expected = 1.0 if key == "B_Cu" else 2.0
            if len(flashes) != 1 or getattr(flashes[0].aperture, "diameter", None) != expected:
                sys.exit(f"{ref}: expected one {expected} mm fiducial flash on {key}")
            fid.append(ref)
            fid_edge[ref] = round(outline.boundary.distance(Point(x, y)), 4)
        if len(fid) != 3:
            sys.exit(f"{key}: expected three assembly fiducials")
        out["layers"][suffix]["fiducials"] = sorted(fid)
        if key == "B_Cu":
            out["fiducial_centres_to_routed_edge_mm"] = dict(sorted(fid_edge.items()))
for kind in ("PTH", "NPTH"):
    f = ExcellonFile.open(plots / f"{STEM}-{kind}.drl", plated=kind == "PTH"); pending = list(native[kind]); worst = 0
    for o in f.objects:
        if not isinstance(o, Flash):
            sys.exit("slot or route in drill file")
        hit = (o.x, o.y, o.aperture.diameter)
        i = min(range(len(pending)), key=lambda i: max(abs(a - b) for a, b in zip(hit, pending[i])))
        e = max(abs(a - b) for a, b in zip(hit, pending.pop(i))); worst = max(worst, e)
        if e > 0.0006:
            sys.exit(f"unmatched {kind} hit {hit}")
    if pending:
        sys.exit(f"missing {kind} drills {pending}")
    out["drills"][kind] = {"hits": len(f.objects), "max_error_mm": round(worst, 6)}
out["pass"] = True
(ROOT / "reports" / "cam-readback.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out))
