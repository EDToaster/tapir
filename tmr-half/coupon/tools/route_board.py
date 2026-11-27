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
from place_board import ORIGIN, W, H, RADIUS

PLACED = ROOT / "build" / (STEM + ".kicad_pcb")
WORK = ROOT / "build" / "route"
SESSION = ROOT / "routing" / (STEM + ".ses")
FINAL = ROOT / (STEM + ".kicad_pcb")
EDGE_INSET = 0.20


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


def export_dsn():
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / (STEM + ".ses")).unlink(missing_ok=True)
    board = k.LoadBoard(str(PLACED)); dsn = WORK / (STEM + ".dsn")
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
    # Ground fill on both layers. Every GND pad is already joined by a trace, so the fill only adds return area.
    x0, y0 = ORIGIN
    for layer in (k.F_Cu, k.B_Cu):
        z = k.ZONE(board); board.Add(z); z.SetLayer(layer); z.SetNet(board.FindNet("GND"))
        z.SetZoneName("GND fill " + board.GetLayerName(layer)); z.SetUuid(k.KIID(uid("zone/" + z.GetZoneName())))
        z.SetLocalClearance(k.FromMM(0.30)); z.SetMinThickness(k.FromMM(0.25))
        z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(k.FromMM(0.30)); z.SetThermalReliefSpokeWidth(k.FromMM(0.40))
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline(); o.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            o.Append(k.VECTOR2I(k.FromMM(x0 + x), k.FromMM(y0 + y)))
    kept = 0
    for attempt in range(8):
        board.BuildConnectivity()
        if not k.ZONE_FILLER(board).Fill(board.Zones()):
            sys.exit("Zone fill failed")
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
    {"dsn": export_dsn, "ses": import_ses}[sys.argv[1]]()
