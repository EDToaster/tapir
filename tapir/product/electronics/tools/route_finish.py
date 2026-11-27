#!/usr/bin/python3
"""Replay checked-in real copper, prove trace-only closure, fill and verify."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from ground_return import add as fill
from route_board import retain_placement
from route_verify import ROOT, verify


def finish(hand):
    stem = f"tapir-{hand}"
    working = ROOT / "build"
    native = ROOT / hand
    core = working / f"hard-routed-{hand}"
    filled = working / f"grounded-{hand}"
    for scratch in (core, filled):
        scratch.mkdir(parents=True, exist_ok=True)
        # These scratch projects are one directory deeper than the native
        # project; the placement generator already wrote this library mapping.
        shutil.copy2(working / hand / "fp-lib-table", scratch / "fp-lib-table")
        for filename in (stem+".kicad_pro", stem+".kicad_sch", "TapirCircuit.kicad_sym", "sym-lib-table"):
            shutil.copy2(native / filename, scratch / filename)
    bare = core / (stem+".kicad_pcb")
    subprocess.run([sys.executable, str(Path(__file__).with_name("route_board.py")),
                    hand, "--session", str(ROOT / "routing" / (stem+".ses")),
                    "--output", str(bare)], check=True)
    if not verify(hand, bare, ROOT / "reports" / "hard-route-only"):
        raise ValueError("Hard routing did not pass; refusing to add planes.")
    # All connectivity already passed above. A second gate validates the
    # expanded no-pour RF exclusion, actual filled copper and exact pad frames.
    board = filled / bare.name
    fill(hand, bare, board)
    retain_placement(working / hand / bare.name, board)
    if not verify(hand, board, working / "filled-drc"):
        raise ValueError("Grounded candidate failed native DRC; not promoted.")
    shutil.copy2(board, native / bare.name)
    if not verify(hand):
        raise ValueError("Final canonical-path verification failed.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hands", nargs="+", choices=("left", "right"))
    for side in ap.parse_args().hands:
        finish(side)
