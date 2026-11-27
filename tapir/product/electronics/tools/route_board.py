#!/usr/bin/python3
"""Route a placed Tapir half locally using KiCad 10 SWIG and FreeRouting 2.5.

Run with the system Python that owns pcbnew. The Java process never needs the
network. Work files stay in build/, not beside source. A result with DRC errors
is not ready for fabrication; run native DRC and schematic parity on the result.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

import pcbnew

ELECTRONICS = Path(__file__).resolve().parents[1]
JAR_HASH = "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7"


def retain_placement(source, routed):
    """Retain the exact KiCad 10 footprint records; only copper was routed.

    In addition to the Specctra coordinate grid, KiCad's own SWIG load/save
    can round a rotated footprint's local pad by 1 nm. Restore *all* original
    records losslessly rather than accepting or hiding any pad-coordinate delta.
    KiCad 10 stores pad/segment nets by name, so there is no index remapping.
    """
    pattern = re.compile(r'^\t\(footprint\b.*?^\t\)$', re.MULTILINE | re.DOTALL)
    ref = re.compile(r'\(property "Reference" "([^"]+)"')
    original = {ref.search(m[0])[1]: m[0] for m in pattern.finditer(source.read_text())}
    seen = set()
    def replace(m):
        key = ref.search(m[0])[1]
        if key in seen:
            raise ValueError(f"Duplicate footprint in routed output: {key}")
        seen.add(key)
        return original[key]
    data = pattern.sub(replace, routed.read_text())
    if not seen or seen != set(original):
        raise ValueError("Placed and routed footprint reference sets differ")
    routed.write_text(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hand", choices=("left", "right"))
    parser.add_argument("--jar", default=os.environ.get("FREEROUTING_JAR"))
    parser.add_argument("--session", type=Path,
                        help="Import a saved physical SES onto unchanged placement instead of rerouting.")
    parser.add_argument("--passes", type=int, default=30)
    parser.add_argument("--threads", type=int, default=1,
                        help="Optimizer thread count; zero skips optimization.")
    parser.add_argument("--input", type=Path, help="Placed board override.")
    parser.add_argument("--output", type=Path, help="Destination board override.")
    parser.add_argument("--work", type=Path, help="Intermediate route-job directory.")
    args = parser.parse_args()
    if not str(pcbnew.GetBuildVersion()).startswith("10."):
        parser.error("KiCad 10 pcbnew is required")
    if not args.session:
        if not args.jar:
            parser.error("Set FREEROUTING_JAR to the official 2.5.0 release jar")
        jar = Path(args.jar).resolve(strict=True)
        with jar.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != JAR_HASH:
                parser.error("FreeRouting jar is not the expected release (sha256 mismatch)")

    stem = f"tapir-{args.hand}"
    source = (args.input or ELECTRONICS / "build" / args.hand /
              f"{stem}.kicad_pcb").resolve(strict=True)
    dest = (args.output or ELECTRONICS / args.hand / f"{stem}.kicad_pcb").resolve()
    work = (args.work or ELECTRONICS / "build" / f"route-{args.hand}").resolve()
    work.mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source == dest:
        parser.error("Placement and routed result must be different files")
    dsn, ses = (work / f"{stem}.{suffix}" for suffix in ("dsn", "ses"))
    # Never import a previous run's session by accident.
    if not args.session:
        ses.unlink(missing_ok=True)
    board = pcbnew.LoadBoard(str(source))
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        sys.exit("KiCad DSN export failed")

    # Deliberately do not exclude nets, layers, or rules. Disable optional
    # remote services, and direct HTTP clients to an unused loopback port.
    command = [] if args.session else [
        "java", "-Djava.awt.headless=true", "-XX:ActiveProcessorCount=2",
        "-Xmx1250m", "-Dhttp.proxyHost=127.0.0.1", "-Dhttp.proxyPort=9",
        "-Dhttps.proxyHost=127.0.0.1", "-Dhttps.proxyPort=9",
        "-jar", str(jar), "-de", str(dsn), "-do", str(ses), "-da",
        "--gui.enabled=false", "--api_server.enabled=false",
        "--user_data_path=" + str(work / "settings"),
        "--router.fanout.enabled=false", "--router.strict_drc=true",
        "--router.autorouter.max_passes=" + str(args.passes),
        "--router.optimizer.enabled=" + ("true" if args.threads > 0 else "false"),
        "-mt", str(max(1, args.threads)), "-is", "sequential",
    ]
    env = dict(os.environ, FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS="true")
    if args.session:
        ses = args.session.resolve(strict=True)
    else:
        subprocess.run(command, check=True, cwd=work, env=env)
    # Specctra uses a coarser coordinate grid than KiCad. Importing a session
    # can round the placements of rotated thumb diodes by ~50 nanometers even
    # when the router never moved anything. Retain the original KiCad frames.
    placements = {f.GetReference(): (tuple(f.GetPosition()), f.GetOrientationDegrees(),
                                     f.GetLayer()) for f in board.GetFootprints()}
    if not ses.exists() or not pcbnew.ImportSpecctraSES(board, str(ses)):
        sys.exit("KiCad SES import failed")
    for footprint in board.GetFootprints():
        pos, angle, layer = placements[footprint.GetReference()]
        angular_error = abs((footprint.GetOrientationDegrees()-angle+180) % 360-180)
        if (angular_error > 0.000001 or footprint.GetLayer() != layer or
            max(abs(a-b) for a, b in zip(pos, footprint.GetPosition())) > 100):
            sys.exit(f"Session unexpectedly moved footprint {footprint.GetReference()}")
        footprint.SetPosition(pcbnew.VECTOR2I(*pos))
    if not list(board.GetTracks()):
        sys.exit("Refusing to save a result with no copper tracks")
    # FreeRouting's congestion heuristics may silently neck traces below the
    # requested class width even when the native design does not permit it.
    # Restore the intended width, then check clearance on that *real copper*
    # with route_verify.py. Never reduce the project rules to fit a route.
    classes = json.loads(source.with_suffix(".kicad_pro").read_text())["net_settings"]["classes"]
    widths = {c["name"]: pcbnew.FromMM(c["track_width"]) for c in classes if "track_width" in c}
    widened = 0
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            continue
        effective = item.GetNet().GetNetClassName().split(",")
        width = next((widths[n] for n in effective if n in widths), widths["Default"])
        if item.GetWidth() < width:
            item.SetWidth(width)
            widened += 1
    copper_ids = set()
    for item in board.GetTracks():
        is_via = item.Type() == pcbnew.PCB_VIA_T
        width = item.GetWidth(pcbnew.F_Cu) if is_via else item.GetWidth()
        spec = (args.hand, item.GetNetname(), item.Type(), item.GetLayer(),
                tuple(item.GetStart()), tuple(item.GetEnd()), width,
                item.GetDrillValue() if is_via else None)
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, "tapir-reva/copper/" + str(spec)))
        if identifier in copper_ids:
            sys.exit("Duplicate physical track/via in routed session")
        copper_ids.add(identifier)
        item.SetUuid(pcbnew.KIID(identifier))
    print(f"Restored {widened} segments to design widths; recheck native clearances.")
    for ext in (".kicad_pro", ".kicad_dru"):
        settings = source.with_suffix(ext)
        if settings.exists() and settings != dest.with_suffix(ext):
            shutil.copyfile(settings, dest.with_suffix(ext))
    # Use the generator's settings directly, rather than serializing incidental
    # session changes to them while saving the board.
    if not pcbnew.SaveBoard(str(dest), board, True):
        sys.exit("Failed to save imported board")
    retain_placement(source, dest)
    print(f"Saved {dest} with {len(list(board.GetTracks()))} track/via items.")


if __name__ == "__main__":
    main()
