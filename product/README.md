# Tapir Rev A engineering handoff

Rev A preserves the Cygnus/Corne 3×6+3 typing layout, ordinary Choc pitch and zero added finger splay. The pointer is beside the right middle thumb, not between typing keys. Its sensing head bridges over the XIAO; its driver is separate. The left thumb controls handle click, right click and hold-to-scroll without giving up a key. The two halves have different boards, enclosures, USB exit directions and firmware roles.

**Disposition: HOLD. No fabrication or purchase is authorized.** This package contains work on the physical product, not a claim that a keyboard has been built. See the [prototype decision](RELEASE.md), [per-component report](validation/REPORT.md) and [machine-readable ledger](validation/results.json) for the digital results, limitations and input fingerprints. See the [bench acceptance card](validation/BENCH.md) before connecting a battery, fitting a cable or claiming runtime. A failing or missing check is not a waiver.

## What to open

| Task | Authoritative deliverable |
| --- | --- |
| Explore the assembled product | [Live workbench](https://www.perplexity.ai/computer/a/06720a1c-6b0b-43b8-b744-eb15799f3c35). The keyboard halves can be inspected separately, with native enclosure meshes, full assembly and motion views. The legacy design studies have separate controls and do not alter the manufactured layout. |
| Verify dimensions or change placement | [Placement contract](design/README.md) and [editable generator](design/generate-geometry.mjs). The same XY and Z datums control PCB, case, projections and checks. |
| Open the circuit | KiCad 10: [left project](electronics/left/tapir-left.kicad_pro), [right project](electronics/right/tapir-right.kicad_pro), [parts and model provenance](electronics/models/README.md), [native reports](electronics/reports/) and [routing workflow](electronics/tools/route.md). Electrical source and PCB are separate per half. |
| Open the case and see how to assemble it | [Editable build123d source](mechanical/), including the pouch organizer, separately supported stick, lid and base. In the workbench ZIP, open `product/mechanical/build/{left,right}/assembly.step`; the same directories hold printable STLs and detailed swept-clearance reports. Clearance/gauge bodies are inspection tools, not pieces to print. |
| Find hardware or qualify an alternative | [Installed BOM and sourcing evidence](sourcing/), [configuration decisions](design-decisions.md), [sensor harness](electronics/pointer-harness.md). A salvaged stick is not electrically or mechanically interchangeable without inspection. |
| Run the keyboard | [ZMK target, native test and build evidence](firmware/). Left is the split peripheral, right is the central with the pointer. Keep the archived binaries with their exact dependency revisions. Files are for separate XIAO nRF52840 Plus modules, not for existing nice!nanos. |
| Approve or reject the prototype | [Requirements and acceptance criteria](requirements.md), [verification ledger](validation/results.json) and [first-article procedures](validation/BENCH.md). Verify the actual print, cable, purchased modules and the exact cell; do not infer hardware readiness from firmware or DRC results. |

## Geometry and inspection

All coordinates are millimetres. Product units are X right, Y toward the palm and Z up from the top of the carrier. The bare-board nominal envelopes are **134.82 × 97.08 mm left** and **134.82 × 106.35 mm right**. These exclude case edges and overhanging parts. PCB coordinates use local XY + (100, 100); assembly CAD uses (X, −Y, Z). The workbench deliberately separates the halves on screen: that gap is not a product dimension. Do not mirror both USB mouths, rotate a native footprint again, or measure from a perspective screenshot.

In the workbench, use **Assembly path** with the relevant half selected. “Lower the PCB” keeps the tray fixed while the capless populated carrier descends; “Close the bezel” shows the cover without keycaps; “Insert the plug gauge” shows external overmold approach at the real receptacle location. The plug gauge is not a claim about contact engagement. The ordinary exploded view is for identifying parts and is not an assembly instruction. Read the native mechanical procedure for battery/lead handling, captive nuts, the pointer bridge, and final caps.

## Reproduce the core digital checks

Run from the repository root. The CAD Python environment is separate from the system Python that ships with KiCad 10. Keep sources, native libraries and project directories together; copying only a board file breaks references. Regenerate the detailed CAD and firmware evidence before running the integrated verifier on a clean checkout.

```sh
(cd workbench && npm ci && npm run check)
node product/design/generate-geometry.mjs --check
# KiCad system Python, after generating the placed carrier baselines:
/usr/bin/python3 product/electronics/tools/route_verify.py left right
# With the pinned build123d environment activated:
python product/electronics/models/model_catalog.py verify
python product/mechanical/build_case.py
python product/release/component_meshes.py
# Run the per-role firmware build per product/firmware/README.md first.
python3 product/validation/verify.py --report-only
# This strict invocation must remain NONZERO while any required gate is open.
python3 product/validation/verify.py --release
```

`npm --prefix workbench run build` creates the viewer and local ZIP with a SHA-256 inventory. It does not send files to a vendor. A source-only checkout does not have every generated mesh or fabrication preview until the native steps above run. Use the downloadable package for the frozen, generated version and the Git source for revision control.

## Power boundary

The [power budget](power-budget.md) shows what a seven-day target leaves for the right-hand radio and MCU with the Sprintek in each documented idle mode. The difference is large enough that idle behavior must be measured before accepting the battery choice.

Rev A uses the non-Sense XIAO Plus and a candidate [protected Adafruit 1570 pack](https://www.adafruit.com/product/1570) per side. The low charge-rate selection is intentional, but current alone cannot qualify a pack: the [BQ25100 charger](https://www.ti.com/lit/ds/symlink/bq25100.pdf) can regulate as high as 4.23 V, while the [specified pack sheet](https://cdn-shop.adafruit.com/product-files/1570/1570datasheet.pdf) calls for 4.20 V without an explicit allowance covering that high limit. The protection trip is not a charge rating. Before real-cell testing, obtain documented compatibility for the exact combination or revise the charge path/pack and repeat design checks. A single agreeable sample is not enough to qualify the tolerances. Perform initial host tests over USB with both cells disconnected; use a current-limited simulator for charger characterization. The seven-day battery budget is a target, not a measured runtime.
