"""Build and re-import a named STEP assembly from the Tapir stack workbench. No duplicated placements."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from build123d import (
    Color,
    Compound,
    Face,
    Shape,
    Unit,
    Wire,
    export_step,
    extrude,
    import_step,
)

HERE = Path(__file__).resolve().parent
KINDS = {
    "rigid": "01 RIGID - proposed component and support solids",
    "envelope": "02 ENVELOPES - motion, access and clearance study",
    "reference": "03 REFERENCE - context, not additional fabricated parts",
}
LINEAR_TOL_MM = 0.00002  # CAD interchange validation, not a manufacturing tolerance.


def ascii_name(value: object) -> str:
    # ASCII names survive AP214 product-name round-trips across STEP readers.
    name = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")


def finite(value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite model coordinate: {value}")
    return number


@dataclass(frozen=True)
class Prism:
    id: str
    label: str
    role: str
    kind: str
    polygon: tuple[tuple[float, float], ...]
    bottom: float
    top: float

    @classmethod
    def from_record(cls, r: dict) -> Prism:
        pts = [(finite(x), finite(y)) for x, y in r["polygon"]]
        # Workbench polygons can be either open loops or repeat the closing point.
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        record = cls(
            str(r["id"]),
            str(r["label"]),
            str(r["role"]),
            str(r["kind"]),
            tuple(pts),
            finite(r["bottom"]),
            finite(r["top"]),
        )
        if (
            record.kind not in KINDS
            or len(pts) < 3
            or record.top <= record.bottom
            or record.area < 1e-9
        ):
            raise ValueError(
                f"Invalid prism: {record.id}, {record.kind}, XY area {record.area}, Z {record.bottom}..{record.top}"
            )
        return record

    @property
    def name(self) -> str:
        return ascii_name(f"{self.id}__{self.label}")

    @property
    def area(self) -> float:
        p = self.polygon
        return (
            abs(
                sum(
                    x * p[(i + 1) % len(p)][1] - y * p[(i + 1) % len(p)][0]
                    for i, (x, y) in enumerate(p)
                )
            )
            / 2
        )

    @property
    def volume(self) -> float:
        return self.area * (self.top - self.bottom)

    @property
    def bounds(self) -> tuple[float, ...]:
        xs, ys = zip(*self.polygon)
        return min(xs), -max(ys), self.bottom, max(xs), -min(ys), self.top

    def to_solid(self) -> Shape:
        # Paper/layout +Y points toward the typist. CAD +Y points to the back;
        # Z is height above the carrier top. Top-view handedness is preserved.
        wire = Wire.make_polygon(
            [(x, -y, self.bottom) for x, y in self.polygon], close=True
        )
        [solid] = extrude(
            Face(wire), amount=self.top - self.bottom, dir=(0, 0, 1)
        ).solids()
        solid.label = self.name
        solid.color = display_color(self)
        return solid


def display_color(p: Prism) -> Color:
    category = f"{p.role} {p.id}".lower()
    if p.kind == "reference":
        return Color(0.60, 0.64, 0.66, 0.26)
    if p.kind == "envelope":
        return Color(0.78, 0.55, 0.20, 0.30)
    if "cap" in category and any(t in category for t in ("rubber", "nub", "pointer")):
        return Color(0.77, 0.28, 0.18)
    if any(t in category for t in ("usb", "jack", "shell")):
        return Color(0.64, 0.68, 0.69)
    if any(
        t in category for t in ("pcb", "board", "xiao", "sensor", "driver", "carrier")
    ):
        return Color(0.20, 0.44, 0.33)
    if any(
        t in category
        for t in ("deck", "leg", "foot", "support", "rail", "clamp", "retention")
    ):
        return Color(0.43, 0.48, 0.55)
    if any(t in category for t in ("fpc", "cable", "flex", "stem", "post")):
        return Color(0.67, 0.47, 0.28)
    return Color(0.72, 0.73, 0.68)


def source_data(options: str, layout_state: str) -> dict:
    result = subprocess.run(
        ["node", str(HERE / "workbench-geometry.mjs"), options, layout_state],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise SystemExit("Workbench geometry export failed:\n" + result.stderr)
    data = json.loads(result.stdout)
    if data["schema"] != 1 or data["units"] != "mm":
        raise ValueError("Unexpected geometry schema or units")
    return data


def assert_matches_source(p: Prism, actual: Shape) -> None:
    if not actual.is_valid or len(actual.solids()) != 1:
        raise ValueError(f"{p.id} is not a valid single solid")
    bb = actual.bounding_box()
    if max(abs(a - b) for a, b in zip((*bb.min, *bb.max), p.bounds)) > LINEAR_TOL_MM:
        raise ValueError(f"{p.id} did not preserve XY/Z bounds: {bb} vs {p.bounds}")
    if not math.isclose(actual.volume, p.volume, abs_tol=1e-5, rel_tol=2e-7):
        raise ValueError(
            f"{p.id} volume {actual.volume} differs from footprint area × height {p.volume}"
        )


def build_tree(prisms: Iterable[Prism]) -> Compound:
    grouped = {k: {} for k in KINDS}
    for p in prisms:
        solid = p.to_solid()
        assert_matches_source(p, solid)
        # Sorting is presentation only; all geometry still comes directly from the same workbench solids.
        if p.kind == "envelope" and p.role in ("switch", "key-sweep"):
            family = (
                "Key_switch_bounds" if p.role == "switch" else "Full_key_motion_sweeps"
            )
        elif p.kind == "envelope" and p.role in ("plug", "rf-screen", "face-reserve"):
            family = "Access_radio_and_face_reservations"
        elif p.kind == "envelope":
            family = "Purchased_part_allowances"
        elif p.kind == "reference":
            family = "Neighboring_keycaps" if p.role == "key" else "Former_layout"
        else:
            family = (
                "Carrier_and_back"
                if p.role in ("carrier", "back")
                else "Stack_and_retention"
            )
        grouped[p.kind].setdefault(family, []).append(solid)
    return Compound(
        label="TAPIR - STACK PACKAGING CONCEPT - NOT FOR FABRICATION",
        children=[
            Compound(
                label=KINDS[k],
                children=[
                    Compound(label=family, children=items)
                    for family, items in groups.items()
                ],
            )
            for k, groups in grouped.items()
            if groups
        ],
    )


def measure(parts: dict[str, Shape], first: str, second: str) -> dict:
    if first not in parts or second not in parts:
        raise ValueError(
            f"Unknown measurement pair: {first}, {second}. Use --list-ids to see available ids."
        )
    a, b = parts[first], parts[second]
    # Separation of exact BReps is non-negative. Use intersection volume to distinguish contact vs intrusion.
    distance = float(a.distance_to(b))
    common = a.intersect(b) if distance < LINEAR_TOL_MM else []
    overlap = sum(s.volume for s in (common or []) if s.volume > 0)
    return {
        "first": first,
        "second": second,
        "distance_mm": round(distance, 6),
        "intersection_mm3": round(overlap, 6),
    }


def closest(parts: dict[str, Shape], first: str, second: str) -> dict:
    """Use AABB lower bounds only to prune; report exact BRep pair distance/overlap."""

    def matches(patterns: str) -> list[str]:
        return [
            id_
            for id_ in parts
            if any(fnmatchcase(id_, pattern.strip()) for pattern in patterns.split(","))
        ]

    ids = {(a, b) for a in matches(first) for b in matches(second) if a != b}
    if not ids:
        raise ValueError(f"No distinct component pairs match {first!r} vs {second!r}")
    boxes = {k: parts[k].bounding_box() for k in {k for pair in ids for k in pair}}

    def lower_bound(pair: tuple[str, str]) -> float:
        a, b = (boxes[k] for k in pair)
        return math.hypot(
            *(
                max(0.0, a0 - b1, b0 - a1)
                for a0, a1, b0, b1 in zip(a.min, a.max, b.min, b.max)
            )
        )

    best = None
    for bound, pair in sorted((lower_bound(pair), pair) for pair in ids):
        if best is not None and bound > best["distance_mm"] + LINEAR_TOL_MM:
            break
        value = measure(parts, *pair)
        # If zero-distance pairs tie, surface the largest positive common volume instead of a benign touch.
        if best is None or (value["distance_mm"], -value["intersection_mm3"]) < (
            best["distance_mm"],
            -best["intersection_mm3"],
        ):
            best = value
    return {"candidate_pairs": len(ids), **best}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "tapir-stacked-thumb.step")
    ap.add_argument(
        "--options",
        default="{}",
        help="JSON object of stackModel options; see workbench/stack.js",
    )
    ap.add_argument(
        "--layout-state",
        default="{}",
        help="JSON object of underlying workbench layout settings",
    )
    ap.add_argument(
        "--physical-only",
        action="store_true",
        help="Exclude envelopes and reference geometry from the STEP",
    )
    ap.add_argument(
        "--list-ids",
        action="store_true",
        help="List current model solids and exit without writing",
    )
    ap.add_argument(
        "--measure",
        nargs=2,
        action="append",
        default=[],
        metavar=("FIRST_ID", "SECOND_ID"),
        help="Report separation / common volume of a pair in the re-imported STEP; repeatable",
    )
    ap.add_argument(
        "--closest",
        nargs=2,
        action="append",
        default=[],
        metavar=("FIRST_IDS", "SECOND_IDS"),
        help="Closest pair across two comma-separated lists of ID globs, e.g. plug vs bridge,foot-*; repeatable",
    )
    args = ap.parse_args()
    snapshot = source_data(args.options, args.layout_state)
    prs = [
        Prism.from_record(r)
        for r in snapshot["solids"]
        if not args.physical_only or r["kind"] == "rigid"
    ]
    if (
        not prs
        or len({p.id for p in prs}) != len(prs)
        or len({p.name for p in prs}) != len(prs)
    ):
        raise ValueError("Empty geometry list or ambiguous part ID/name")
    if args.list_ids:
        print("\n".join(f"{p.id}\t{p.kind}\t{p.label}" for p in prs))
        return
    compound = build_tree(prs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not export_step(
        compound, args.output, unit=Unit.MM, timestamp="2000-01-01T00:00:00"
    ):
        raise RuntimeError("STEP export did not succeed")
    back = import_step(args.output)
    by_label = {s.label: s for s in back.leaves}
    if set(by_label) != {p.name for p in prs} or len(back.leaves) != len(prs):
        raise ValueError("Names or STEP assembly structure changed during round trip")
    for p in prs:
        assert_matches_source(p, by_label[p.name])
    by_id = {p.id: by_label[p.name] for p in prs}
    sig = hashlib.sha256(
        json.dumps(snapshot["solids"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(
        json.dumps(
            {
                "step": str(args.output),
                "source_solids_sha256": sig,
                "scope": "nominal packaging envelopes only",
                "stack_options": snapshot["options"],
                "reimport_validated_parts": {
                    k: sum(p.kind == k for p in prs) for k in KINDS
                },
                "measurements": [measure(by_id, *pair) for pair in args.measure],
                "nearest_pairs": [closest(by_id, *pair) for pair in args.closest],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
