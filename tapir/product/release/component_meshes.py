"""Tessellate the same local STEP models used by the PCB, in native millimeters.

Use the product/mechanical pinned Python environment. Source files, license
notices, and each approximation are recorded under product/electronics/models.
"""
from pathlib import Path
from build123d import export_stl, import_step
ROOT=Path(__file__).resolve().parents[2]
src=ROOT/"product/electronics/models"
out=ROOT/"product/electronics/build/webmodels"
out.mkdir(parents=True,exist_ok=True)
for step in sorted(src.glob("*.step")):
    dest=out/(step.stem+".stl")
    if dest.exists() and dest.stat().st_mtime_ns>=max(step.stat().st_mtime_ns,Path(__file__).stat().st_mtime_ns):continue
    # Portable WebGL preview only. The dimensional tests use source BReps,
    # not this coarser tessellation of 42 repeated switch bodies.
    if not export_stl(import_step(step),dest,tolerance=.10,angular_tolerance=.45):raise ValueError(step)
    print(dest.name)
