"""Fast ENVELOPE gate: full length, remote self-crossings, battery, plug and printed materials before STEP."""

import json, sys
from shapely.geometry import LineString
from design import layout, cover, tray, cassette, bridge, poly, EMPTY, grow, join
from harness import wire_plan, whole_wire, layered_overlap, analog_bands
from build_case import HERE, GEO, write_json

sys.path.insert(0, str(HERE.parent / "validation"))
from wire import clearance as independent_self_check


def run(geometry=GEO, output=HERE / "build" / "preflight"):
    results = []
    for hand, h in json.loads(geometry.read_text())["halves"].items():
        d = output / hand
        d.mkdir(parents=True, exist_ok=True)
        q = layout(h)
        plan, wire = wire_plan(q)
        info, layers = whole_wire(q, plan)
        path = d / "battery-wire-105mm.json"
        write_json(path, info)
        self_status, detail = independent_self_check(path)
        analog = (
            LineString([p[:2] for p in h["wiring"]["sensorToDriver"]["points"]]).buffer(
                1.7, quad_segs=6
            )
            if "sensorToDriver" in h["wiring"]
            else EMPTY
        )
        mat = lambda levels, name, color: levels
        channel = grow(wire, 0.35)
        bodies = {
            "tray": tray(q, mat),
            "organizer": cassette(q, channel, mat),
            "cover": cover(q, channel, analog, mat),
        }
        if "bridge" in q.c:
            bodies["bridge"] = bridge(q, mat)
        jst = [
            (0, 6.4, join(poly(q.c["batteryConnectorCourt"]), poly(q.c["batteryPlug"])))
        ]
        against = {k: round(layered_overlap(layers, s), 6) for k, s in bodies.items()}
        against["maximum-pack"] = round(
            layered_overlap(layers, [(0, 4.30, q.pack_max)]), 6
        )
        plug = {k: round(layered_overlap(jst, s), 6) for k, s in bodies.items()}
        ab = analog_bands(h)
        analog_collisions = (
            {k: round(layered_overlap(ab, s), 6) for k, s in bodies.items()}
            if ab
            else {}
        )
        ok = self_status == "PASS_DIGITAL" and not any(
            v > 0.00002
            for v in (*against.values(), *plug.values(), *analog_collisions.values())
        )
        row = {
            "hand": hand,
            "status": "PASS_NOMINAL" if ok else "FAIL",
            "wire_self_check": detail,
            "wire_vs_material_mm3": against,
            "jst_vs_prints_mm3": plug,
            "four_wire_analog_vs_prints_mm3": analog_collisions,
            "centerline_mm": info["centerlineLength_mm"],
            "smallestModeledCornerRadius_mm": info["roundJunctionMinRadius_mm"],
        }
        results.append(row)
        print(json.dumps(row), flush=True)
    write_json(output / "results.json", results)
    if not all(r["status"] == "PASS_NOMINAL" for r in results):
        raise SystemExit(2)


if __name__ == "__main__":
    run()
