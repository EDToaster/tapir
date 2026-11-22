"""Generate BOTH assembled-coordinate enclosure prototypes, editable STEP, STL and mechanically audited data."""

import argparse
import hashlib
import json
from pathlib import Path
from copy import copy
from build123d import Compound, Location, export_step, import_step
from shapely.geometry import LineString
from kernel import (
    bounds,
    common,
    disk,
    grow,
    hex_nut,
    join,
    prism,
    write_mesh,
    EMPTY,
)
from design import (
    FLOOR,
    PCBBOT,
    BEZEL_TOP,
    SHELF_TOP,
    PCB_NUT_TOP,
    CASE_NUT_TOP,
    rect_axis,
    layout,
    poly,
    tray,
    cassette,
    bridge,
    cover,
)
from harness import wire_plan, whole_wire, ribbon_step, layered_overlap, analog_bands

HERE = Path(__file__).resolve().parent
GEO = HERE.parent / "design" / "geometry.json"
MODELS = HERE.parent / "electronics" / "models"
PARTS = {
    "bottom-tray": ("tray", "Lower tray, underside captive-nut wells"),
    "service-bezel": (
        "cover",
        "Service bezel with pouch hood and independent case screws",
    ),
    "pouch-organizer": ("retainer", "Removable pouch isolation shelf and lead store"),
    "pointer-bridge": ("bridge", "Captive, independently supported pointer bridge"),
}
MOTION = [
    {
        "id": "pcb_into_tray",
        "moving": "populated carrier, without detachable pouch/bridge/caps",
        "deltaCAD": [0, 0, -24],
        "startZoffset_mm": 24,
        "endZoffset_mm": 0,
    },
    {
        "id": "cassette_into_tray",
        "moving": "organizer over protected cell (disconnected wiring)",
        "deltaCAD": [0, 0, -18],
        "startZoffset_mm": 18,
        "endZoffset_mm": 0,
    },
    {
        "id": "bezel_onto_caseless_assembly",
        "moving": "upper bezel; all removable keycaps off, USB detached",
        "deltaCAD": [0, 0, -24],
        "startZoffset_mm": 24,
        "endZoffset_mm": 0,
    },
    {
        "id": "usb_straight_insertion",
        "moving": "USB plug/overmold from 36 mm outside mating mouth",
        "travel_mm": 36,
        "state": "closed case",
    },
]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rendered(name, rec):
    return prism(poly(rec), rec["bottom"], rec["top"], name)


def pack_model(file, record, angle=0):
    if file not in pack_model.cache:
        pack_model.cache[file] = import_step(MODELS / file)
    base = pack_model.cache[file]
    # Strip imported assembly tree from the instance; keep shared underlying BRep with distinct local placement.
    s = Compound(base.wrapped).located(
        Location((record["x"], -record["y"], 0), (0, 0, 1), angle - record.get("a", 0))
    )
    s.label = record.get("id", file)
    return s


pack_model.cache = {}


def hardware(q):
    c = q.c
    special = {
        k: pack_model(file, c[k], angle)
        for k, file, angle in (
            ("batteryConnector", "JST_S2B_PH_SM4_TB_fit.step", 0),
            ("powerSwitch", "SW_SPDT_PCM12.step", 0),
            ("xiao", "XIAO_nRF52840_Plus_nonSense_fit.step", 90),
        )
    }
    return special


def process(hand, h, build, geo_sig, mode):
    dest = build / hand
    dest.mkdir(parents=True, exist_ok=True)
    q = layout(h)
    c = q.c
    wp, wvol = wire_plan(q)
    ana = EMPTY
    if "sensorToDriver" in h["wiring"]:
        pts = h["wiring"]["sensorToDriver"]["points"]
        ana = LineString([p[:2] for p in pts]).buffer(1.7, quad_segs=6)
    print(hand, "building printable bodies", flush=True)
    wire_slot = grow(wvol, 0.35)
    p = {
        "bottom-tray": tray(q),
        "pouch-organizer": cassette(q, wire_slot),
        "service-bezel": cover(q, wire_slot, ana),
    }
    if "bridge" in c:
        p["pointer-bridge"] = bridge(q)
    manifest = []
    for id_, part in p.items():
        path = dest / (id_ + ".stl")
        n = write_mesh(part, path)
        role, title = PARTS[id_]
        manifest.append(
            {
                "id": hand + "-" + id_,
                "hand": hand,
                "role": role,
                "label": title,
                "stl": str(path.relative_to(build)),
                "bounds": bounds(part),
                "sha256": fingerprint(path),
                "triangles": n,
            }
        )
    write_json(dest / "mesh-manifest.json", manifest)
    if mode == "meshes":
        return manifest, None
    print(hand, "checking solids and motion", flush=True)
    pan = p["bottom-tray"]
    lid = p["service-bezel"]
    org = p["pouch-organizer"]
    checks = []
    ctx = []
    gauges = []
    wire_info, w_layers = whole_wire(q, wp)
    write_json(dest / "battery-wire-105mm.json", wire_info)
    wp["full_three_dimensional_centerline"] = wire_info
    ctx.append(ribbon_step(wire_info))
    import sys

    sys.path.insert(0, str(HERE.parent / "validation"))
    from wire import clearance as independent_self_check

    verdict, detail = independent_self_check(dest / "battery-wire-105mm.json")
    checks.append(
        {
            "id": "nonlocal_wire_self_clearance",
            "status": "PASS_NOMINAL"
            if verdict == "PASS_DIGITAL"
            else "FAIL_SELF_CROSS",
            "description": detail,
        }
    )
    ab = analog_bands(h)
    if ab:
        analog_reference = ribbon_step({"centerlineXYZ_mm":h["wiring"]["sensorToDriver"]["points"]},1.4,.4)
        analog_reference.label = "Proposed_four_conductor_analog_harness_reference"
        ctx.append(analog_reference)
        for id_, body in p.items():
            ov = layered_overlap(ab, body._material_layers)
            checks.append(
                {
                    "id": "four_analog_wires_vs_" + id_,
                    "status": "PASS_NOMINAL" if ov < 0.00002 else "FAIL_INTERSECTION",
                    "conservative_common_mm3": round(ov, 6),
                    "description": "Canonical four-wire sensor/driver route bounded by 2.8 × 0.8 mm, subdivision at 0.4 mm arc length and 0.20 mm in Z; actual solder and wire fixation open.",
                }
            )
    for id_, material in [(k, v._material_layers) for k, v in p.items()] + [
        ("maximum_pack", [(0, 4.30, q.pack_max)])
    ]:
        v = layered_overlap(w_layers, material)
        checks.append(
            {
                "id": "full_105mm_wiring_vs_" + id_,
                "status": "PASS_NOMINAL" if v < 0.00002 else "FAIL_INTERSECTION",
                "conservative_common_mm3": round(v, 6),
                "description": "Complete uncut centerline, rectangular width/height allowances bounded by conservative 0.25-mm Z bands; no press-fit, pull or vendor bend-radius qualification.",
            }
        )

    def check(id_, a, b, explain):
        v = common(a, b)
        passed = v < 0.00002
        checks.append(
            {
                "id": id_,
                "status": "PASS_NOMINAL" if passed else "FAIL_INTERSECTION",
                "common_mm3": round(v, 7),
                "description": explain,
            }
        )
        if not passed:
            print(hand, "INTERFERENCE", id_, v, flush=True)

    def make(name, pg, z0, z1, store=True):
        s = prism(pg, z0, z1, name, (0.79, 0.64, 0.44, 0.30))
        if store:
            gauges.append(s)
        return s

    def group(*parts):
        return Compound(children=[copy(x) for x in parts])

    mounts = join(
        *[disk(t["x"], t["y"], t["diameter"] / 2) for t in h["mountingHoles"]]
    )
    carrier = prism(
        q.outline.difference(mounts),
        PCBBOT,
        0,
        "Carrier_context_outline_four_NPTH_only",
        (0.13, 0.43, 0.31),
    )
    ctx.append(carrier)
    # The contract includes columns of tail/solder and diodes (all of their actual projected keep-outs).
    back = [r for r in q.records if r["role"] in ("switch-tail", "matrix-diode")]
    levels = sorted({r["bottom"] for r in back})
    tails = group(
        *[
            make(
                "backside_Z" + str(z),
                join(*[poly(r) for r in back if r["bottom"] == z]),
                z,
                PCBBOT,
                False,
            )
            for z in levels
        ]
    )
    tails.label = "Backside_electronics_and_solder_envelopes"
    ctx.append(tails)
    bmax = make("PKCELL_max_12_3x32x4_3", q.pack_max, 0, 4.30)
    ctx.append(rendered("Adafruit_1570_nominal", c["battery"]))
    special = hardware(q)
    gauge_usb = make("USB_IF_QF_straight_overmold_sweep", q.usb, 0, 6.50)
    plugged = group(*p.values())
    check(
        "usb_enclosure",
        plugged,
        gauge_usb,
        "36 mm overmold translated along external mouth normal; 12.35 × 6.50 mm maximum rectangular gauge, 38 mm reservation. No connector internal mating certification.",
    )
    m = q.mouth
    d = m["direction"]

    def port(width, at0, at1):
        return rect_axis(m["x"], m["y"], *d, width, at0, at1)

    # Named Qualtek drawing: pin/shell projection 6.65 ± .20, molded-end reference 36, cable Ø3.5 ± .2.
    # Drawing does NOT dimension the overmold W/H or receptacle stop: substitute USB-IF max and seat shoulder flush to F.Fab face.
    metal = make(
        "Qualtek_3021091_mating_tip_seated_6_85_deep_conservative",
        port(8.50, -6.85, 0),
        2.035,
        4.465,
    )
    body = make(
        "Qualtek_3021091_max_body_36mm_straight_sweep_from_36",
        port(12.35, 0, 72),
        0,
        6.5,
    )
    cable = make(
        "Qualtek_3021091_Jacket_OD_3_70_extended_straight",
        port(3.70, 36, 92),
        1.40,
        5.10,
    )
    check(
        "Qualtek_3021091_01M_named_cable_to_face",
        plugged,
        group(metal, body, cable),
        "Named 1 m cable. 6.85 mm conservative projected metal × assumed 8.50 width × 2.43 thickness centered at Z3.25; shoulder at receptacle F.Fab front, full 36 mm external withdrawal. 36 mm REF used as conservative external overmold length; cross-section substituted from USB-IF. External enclosure only, no proof of internal tongue, retention/fully latched stop, or cable bend.",
    )
    check(
        "closure_interfaces",
        pan,
        lid,
        "Assembled bezel versus pan; zero volume permits designed seam contact.",
    )
    check(
        "cassette_tray", pan, org, "Organizer feet rest on PCB, not on floor or wall."
    )
    check(
        "cassette_hood",
        lid,
        org,
        "Hood guides and capture ledges vs stationary cassette; no plastic interpenetration.",
    )
    check(
        "max_cell_separator",
        org,
        bmax,
        "Worst drawing dimensions vs separator; end growth and thickness allowances modeled separately.",
    )
    check(
        "max_cell_enclosure",
        group(pan, lid),
        bmax,
        "Maximum cell vs seated enclosure, no common material.",
    )
    check(
        "carrier_in_tray",
        pan,
        carrier,
        "Full bare board, four NPTH; seating on boss faces permitted.",
    )
    check(
        "solder_and_diodes_vs_tray",
        pan,
        tails,
        "All underside canonical pins/diodes vs tray and all bosses.",
    )
    check(
        "full_key_motion_vs_plastics",
        plugged,
        make("Full_key_sweeps", q.keycaps, 3.6, 10.6),
        "All 21 conservative moving MBK cap boxes, including the pressed skirt.",
    )
    check(
        "released_switches_vs_cover",
        lid,
        make("Choc_15mm_flange_screens", q.switch_union, 0, 8),
        "21 nominal 15 mm Choc flange/switch boxes through 15.76 mm nominal openings.",
    )
    for n, v in special.items():
        check(
            "native_" + n + "_vs_all_plastics",
            plugged,
            v,
            "Imported local STEP with preserved board frame. XIAO/JST are supplier-drawing-derived fit models, not supplier assembly solids.",
        )
    # Both transitions are continuous, not samples at 0/25/50/75/100%. A uniform vertical move sweeps each projected prism.
    check(
        "insert_carrier_over_bosses",
        pan,
        make("Board_lowering_24mm", q.outline.difference(mounts), PCBBOT, 24),
        "PCB final position to +24 mm, reversed for insertion; first contact is its underside on boss tops.",
    )
    tail_sweep = group(
        *[
            make(
                "Tail_sweep_" + str(z),
                join(*[poly(r) for r in back if r["bottom"] == z]),
                z,
                24,
                False,
            )
            for z in levels
        ]
    )
    check(
        "insert_as_soldered_board",
        pan,
        tail_sweep,
        "Continuous swept projection from as-soldered tail/diode bottom to +24; caps, pouch and bridge removed.",
    )
    check(
        "cassette_vertical_onto_cell",
        org,
        make("Cell_relative_to_descending_cassette", q.pack_max, -18, 4.3, False),
        "Inverse motion: max pack extruded downward by 18 mm relative to descending cassette; leads unplugged.",
    )
    # For moving cover vs fixed parts, sweep the fixed parts downward RELATIVE to cover, not upward.
    switch_slide = make(
        "Switches_relative_to_descending_bezel", q.switch_union, -24, 8, False
    )
    check(
        "lower_bezel_capless_keys",
        lid,
        switch_slide,
        "24 mm continuous capless release/installation; reserve encompasses whole fixed flange. Keycaps must be removed.",
    )
    for name, mask, zt in [
        ("cassette_shelf", q.cassette, SHELF_TOP),
        ("cassette_center_form", q.spindle, 10.25),
        ("controller_and_shell", join(poly(c["xiao"]), poly(c["usbShell"])), 5.15),
        (
            "power_actuator",
            join(poly(c["powerSwitchCourt"]), poly(c["powerLever"])),
            2.25,
        ),
        ("JST_header", poly(c["batteryConnectorCourt"]), 6.4),
    ]:
        check(
            "lower_bezel_over_" + name,
            lid,
            make("Inverse_" + name, mask, -24, zt, False),
            "Continuous relative displacement during full 24 mm cover closure.",
        )
    if "driver" in c:
        check(
            "lower_bezel_over_driver",
            lid,
            make("Inverse_driver", q.driver, -24, c["driver"]["top"], False),
            "Driver under service roof.",
        )
    if h["buttons"]:
        check(
            "mouse_unpressed_switch_vs_bezel",
            lid,
            group(*[pack_model("SW_SPST_PTS810.step", r) for r in h["buttons"]]),
            "Real C&K switch at rest vs integral paddle; hinge load/travel/endurance not validated.",
        )
    jst_slide = make(
        "JST_connector_and_12mm_unplug_space",
        join(poly(c["batteryConnectorCourt"]), poly(c["batteryPlug"])),
        0,
        6.4,
    )
    check(
        "JST_withdrawal_vs_all_prints",
        plugged,
        jst_slide,
        "12 mm provisional PH withdrawal-direction solid and 6.4 mm conservative height; apply only with leads freed.",
    )
    check(
        "power_switch_access",
        plugged,
        make("Edge_power_actuator_access", q.power_path, 0.35, 2.25),
        "PCB-to-open-air actuation path; accessibility to an actual fingertip/tool remains physical.",
    )
    check(
        "wire_lane_closed_case",
        plugged,
        make("Candidate_wire_lane_width_2_2_height_1_2", wvol, 0.3, 1.5),
        "Flat two-wire planar run in molded service slot; does not prove vertical entry/two-turn winding.",
    )
    tools = join(
        *[disk(s["x"], s["y"], s["toolDiameter"] / 2) for s in h["mountingHoles"]]
    )
    check(
        "PCB_screw_tool_access",
        lid,
        make("PCB_driver_access_caps_removed", tools, 0, 24, False),
        "Conservative 4.4 mm tool shafts to all four PCB screws; remove caps.",
    )
    closure_g = join(*[disk(x, y, 1.9) for x, y in q.seats])
    check(
        "case_screw_tool_external",
        group(org, *([p["pointer-bridge"]] if "bridge" in c else [])),
        make("External_driver_paths", closure_g, BEZEL_TOP, 24, False),
        "Vertical case screwdriver path with cap removal.",
    )
    if "bridge" in c:
        br = p["pointer-bridge"]
        check(
            "bridge_seated_cover",
            br,
            lid,
            "Captive low tabs under upper bezel, deck clear in service opening.",
        )
        check(
            "bridge_seated_tray",
            br,
            pan,
            "No intersection with tray; feet supported by carrier, not PCB modules.",
        )
        check(
            "bridge_native_controller",
            br,
            special["xiao"],
            "Exact sourced local XIAO fit STEP, including mount standoff and USB shell.",
        )
        check(
            "bridge_usb",
            br,
            gauge_usb,
            "External maximum overmold vs captive bridge, feet, and tabs.",
        )
        ctx.append(rendered("Detached_pointer_driver_envelope", c["driver"]))
        sensor_pattern = join(
            *[disk(t["x"], t["y"], t["diameter"] / 2) for t in c["sensorHoles"]]
        )
        ctx.append(
            prism(
                poly(c["sensor"]).difference(sensor_pattern),
                c["sensor"]["bottom"],
                c["sensor"]["top"],
                "Detached_sensor_with_four_mounting_holes",
            )
        )
        pads = join(*[disk(t["x"], t["y"], 1.43) for t in c["sensorHoles"]]).difference(
            sensor_pattern
        )
        ctx.append(
            prism(
                pads,
                c["bridge"]["top"],
                c["sensor"]["bottom"],
                "Four_provisional_dielectric_bond_lands_not_active_face",
                (0.66, 0.50, 0.29),
            )
        )
        for k in ("shaft", "rubberCap"):
            ctx.append(rendered("Pointer_" + k, c[k]))
        # Every feature above the cover opening: permit tabs below it, assume no installed cable during cover removal.
        for role, mask, zt in [
            ("deck", q.bridge, c["bridge"]["top"]),
            ("feet", q.feet, c["bridge"]["bottom"]),
            ("tabs", q.bridge_tabs, 0.9),
        ]:
            check(
                "lower_bezel_over_bridge_" + role,
                lid,
                make("Bridge_" + role + "_inverse_path", mask, -24, zt, False),
                "24 mm continuous inverse cover sweep.",
            )
        # capture is demonstrated by a *positive* overlap with the cover when the bridge tries to rise.
        up = br.moved(Location((0, 0, 0.50)))
        up._material_layers = [
            (a + 0.5, b + 0.5, pg) for a, b, pg in br._material_layers
        ]
        captured = common(up, lid)
        checks.append(
            {
                "id": "anti_lift_tabs_engage",
                "status": "PASS_NOMINAL" if captured > 0.05 else "FAIL_LOOSE",
                "common_mm3_at_0_50_lift": round(captured, 5),
                "description": "Deliberate negative control: moving bridge upwards 0.50 mm produces tab/cover intersection.",
            }
        )
    # Include all seated bolt + nut fit envelopes, with the actual selected dimensions, not the tool diameter.
    for i, (x, y) in enumerate(q.all_seats):
        cl = i >= len(q.pcb_seats)
        under = BEZEL_TOP if cl else 0.0
        length = 8 if cl else 6
        cap = CASE_NUT_TOP if cl else PCB_NUT_TOP
        nut = prism(
            hex_nut(x, y, 4.0).difference(disk(x, y, 1.02)),
            cap - 1.60,
            cap,
            f"Nut_{i + 1}_M2_AF4",
        )
        shaft = prism(
            disk(x, y, 1.0), under - length, under, f"Screw_{i + 1}_M2x{length}_shank"
        )
        head = prism(disk(x, y, 1.75), under, under + 1.3, f"Screw_{i + 1}_button_head")
        ctx.extend((nut, shaft, head))
        check(
            "bolt_nut_seating_" + str(i + 1),
            plugged,
            group(nut, shaft, head),
            "Selected M2 button-head and captive nut vs plastic; smooth shank is a non-thread gauge.",
        )
    for id_, under, length, cap in [
        ("PCB_M2x6", 0, 6, PCB_NUT_TOP),
        ("case_M2x8", BEZEL_TOP, 8, CASE_NUT_TOP),
    ]:
        ztip = under - length
        engagement = round(max(0, cap - max(cap - 1.60, ztip)), 3)
        checks.append(
            {
                "id": id_ + "_nut_engagement",
                "status": "PASS_NOMINAL"
                if engagement == 1.60 and ztip > FLOOR
                else "FAIL_ENGAGEMENT",
                "engagement_mm": engagement,
                "tipAboveDeskPlane_mm": round(ztip - FLOOR, 3),
                "description": "Full nominal 1.60 mm nut engagement, threaded lead-in/tolerances, torque and pull-out not verified.",
            }
        )
    # Load the actual populated carrier at the KiCad export's mounting plane. Do not approximate board placement.
    pcb_path = HERE.parent / "electronics" / "step" / f"tapir-{hand}-populated.step"
    if not pcb_path.exists():
        raise FileNotFoundError(
            f"Missing populated board STEP; generate it with ECAD tools first: {pcb_path}"
        )
    assembled = import_step(pcb_path)
    actual = []
    for child in assembled.children:
        item = Compound(child.wrapped).moved(Location((0, 0, -1.595)))
        item.label = child.label
        actual.append(item)
    if len(actual) < 50:
        raise ValueError("Incomplete native populated assembly: " + str(pcb_path))
    hit = []
    for child in actual:
        for part_id, printed_body in p.items():
            overlap = common(child, printed_body)
            if overlap > 0.00002:
                hit.append(
                    {
                        "model": child.label,
                        "location": bounds(child),
                        "print": part_id,
                        "common_mm3": round(overlap, 7),
                    }
                )
    checks.append(
        {
            "id": "actual_populated_KiCad_STEP_vs_all_prints",
            "status": "FAIL_INTERSECTION" if hit else "PASS_NOMINAL",
            "model": pcb_path.name,
            "model_sha256": fingerprint(pcb_path),
            "material_instances": len(actual),
            "applied_Z_mm": -1.595,
            "collisions": hit,
            "description": "All top-level PCB and component STEP instances, including backside parts, against every printed body. Independent of canonical envelope test. Excludes cell/pointer/driver unless present in PCB assembly.",
        }
    )
    physical = [
        *p.values(),
        *actual,
        *[
            x
            for x in ctx
            if not x.label.startswith(("Uncut_", "Backside_", "Carrier_context_"))
        ],
    ]
    extents = [bounds(v) for v in physical]
    actual_bounds = [(min if i < 3 else max)(a[i] for a in extents) for i in range(6)]
    assm = Compound(
        label="Tapir_" + hand + "_mechanical_prototype",
        children=[
            Compound(label="Printed_components", children=list(p.values())),
            Compound(label="Actual_populated_KiCad_STEP", children=actual),
            Compound(label="Physical_context_not_ECAD_copper", children=ctx),
            Compound(
                label="Reference_keepouts_and_motion_HIDE_for_assembled_view",
                children=gauges,
            ),
        ],
    )
    path = dest / "assembly.step"
    export_step(assm, path)
    # Check printable STEP round-trip independently of purchasable/reference groups.
    step = dest / "printable-parts.step"
    export_step(
        Compound(label=hand + "_printable", children=[copy(x) for x in p.values()]),
        step,
    )
    back_step = import_step(step)
    assert len(back_step.solids()) == len(p) and all(
        s.is_valid for s in back_step.solids()
    )
    for native_part in p.values():
        match = next(
            (s for s in back_step.children if s.label == native_part.label), None
        )
        if (
            match is None
            or max(abs(v - w) for v, w in zip(bounds(match), bounds(native_part)))
            > 0.00005
            or abs(match.volume - native_part.volume) > 0.001
        ):
            raise ValueError("Printable STEP roundtrip failed: " + native_part.label)
    tests = {
        "hand": hand,
        "geometry_sha256": geo_sig,
        "mesh_sha256": {Path(x["stl"]).name: x["sha256"] for x in manifest},
        "assembly_sha256": fingerprint(path),
        "printable_step_sha256": fingerprint(step),
        "enclosure_bounds": bounds(plugged),
        "assembled_physical_bounds": actual_bounds,
        "physical_bounds_scope": "Printed bodies, all native KiCad board/components, case hardware, pack/driver/sensor stock fields; excludes keepouts, loose cable and optional desk feet.",
        "allowance_budget_mm": {
            "changes_are_assumed_not_measured": True,
            "print_inward_per_surface": 0.20,
            "PCB_or_module_edge_error": 0.10,
            "PCB_edge_radial_nominal": 0.50,
            "PCB_edge_remaining": 0.20,
            "USB_side_nominal": 0.55,
            "USB_bottom_nominal": 0.65,
            "pouch_headroom_over_max": 1.10,
            "pouch_headroom_after_print_and_0_15_insulator": 0.75,
            "solder_underfloor_nominal": 1.25,
        },
        "mounts_assembled_XY": q.pcb_seats,
        "case_screws_assembled_XY": q.seats,
        "paths": MOTION,
        "wire_plan": wp,
        "checks": checks,
        "assembly_bytes": path.stat().st_size,
    }
    write_json(dest / "clearances.json", tests)
    return manifest, tests


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geometry", type=Path, default=GEO)
    ap.add_argument("--build", type=Path, default=HERE / "build")
    ap.add_argument("--hand", choices=["left", "right", "both"], default="both")
    ap.add_argument("--meshes-only", action="store_true")
    ap.add_argument(
        "--manifest-only",
        action="store_true",
        help="Collect existing per-hand STLs without performing a build.",
    )
    args = ap.parse_args()
    g = json.loads(args.geometry.read_text())
    sig = fingerprint(args.geometry)
    for hand, h in g["halves"].items():
        if not args.manifest_only and args.hand in ("both", hand):
            process(hand, h, args.build, sig, "meshes" if args.meshes_only else "full")

    def collect(name):
        files = [args.build / h / name for h in ("left", "right")]
        return [json.loads(v.read_text()) for v in files if v.exists()]

    m = [s for a in collect("mesh-manifest.json") for s in a]
    write_json(
        args.build / "viewer-manifest.json",
        {
            "schema": 1,
            "units": "mm",
            "coordinates": "CAD: x=geometry.x, y=-geometry.y, z=geometry.z; per-hand local",
            "parts": m,
        },
    )
    if not args.meshes_only and not args.manifest_only:
        all_results = collect("clearances.json")
        write_json(
            args.build / "clearances.json",
            {"schema": 1, "units": "mm", "input_sha256": sig, "halves": all_results},
        )
        failures = [
            (a["hand"], c["id"], c.get("common_mm3"))
            for a in all_results
            for c in a["checks"]
            if c["status"].startswith("FAIL")
        ]
        print("FAILURES:", failures, flush=True)
        if failures:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
