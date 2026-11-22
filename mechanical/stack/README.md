# Stacked thumb pointer: editable packaging assembly

`tapir-stacked-thumb.step` is a millimeter STEP assembly of the proposed right-thumb-pointer stack. It is a packaging study, **not a routed carrier, dimensioned enclosure, verified donor assembly, or orderable part**. Open the STEP assembly tree to isolate the sensor head, separate driver, populated-controller study, adjacent keys, proposed restraints, and the access volumes that make the stack larger than the two boards alone.

## Regenerate from the same geometry as the workbench

The footprint, position, and top/bottom height of **every** emitted solid come directly from `stackModel()` in `workbench/stack.js` at export time. `workbench-geometry.mjs` is a thin JSON bridge to that function; `assembly.py` is the editable build123d implementation of the resulting planar solids. Change a dimension in the workbench model first, then regenerate the STEP. No independently positioned MCAD stack is checked in.

From the repository root, with Node 20 and `uv` installed:

```sh
(cd workbench && npm ci)
uv venv --python 3.12.15 .venv-stack
uv pip sync --python .venv-stack/bin/python mechanical/stack/requirements.lock
.venv-stack/bin/python mechanical/stack/assembly.py
```

The lock file records the versions actually used on Linux x86_64, including build123d 0.13.0 and the OCCT 8.0.1.1.0 Python wheel. The generation command reopens the STEP, verifies the **name, validity, one-solid topology, six bounds, and volume of every component** against the layout polygons, and prints an audit summary. The round-trip tolerance is an interchange check, not a machining tolerance.

```sh
# Inspect actual part identifiers in the current workbench revision.
.venv-stack/bin/python mechanical/stack/assembly.py --list-ids

# Omit all envelope and reference groups when a rigid-only context is wanted.
.venv-stack/bin/python mechanical/stack/assembly.py --physical-only --output /tmp/tapir-rigid.step

# Modify stack options or underlying layout state using their workbench property names.
# --measure FIRST_ID SECOND_ID can be repeated with any IDs from --list-ids.
.venv-stack/bin/python mechanical/stack/assembly.py --layout-state '{"switchType":"ulp"}' --output /tmp/tapir-ulp.step
```

## Reading the file

- **Coordinates:** The carrier PCB top is `Z=0`. CAD `X = workbench x`, CAD `Y = −workbench y` (positive CAD Y points away from the user), and CAD `Z = workbench height`. The coordinate reflection puts the right half in the same handed orientation as the workbench when viewed from above.
- **Groups:** `01 RIGID` contains nominal component/support solids. `02 ENVELOPES` contains reservations or movement/access volumes, not stock to fabricate. `03 REFERENCE` contains comparison/context geometry, not additional material in the proposed stack. Toggle the latter two groups before judging an apparent interference. Some STEP readers do not preserve transparency.
- **Measurements:** `--measure` reports the minimum geometric separation and, at contact, the common solid volume using re-imported OpenCascade geometry. A zero distance may be seating, interference, or a swept volume crossing a reference body. Check the pair’s role as well as the overlap volume; neither is evidence of an insertion path, cable bend compliance, or manufacturing clearance under tolerances.
- **Limits:** Polygon extrusions preserve the workbench’s nominal footprints, not a supplier STEP model’s hardware details. Do not drill, tool, route an RF antenna underneath metal, approve cell clearance, or order parts using this STEP. Validate the exact module, connected cable/plug, screw and tool access, pad/contact stack, flex routing, actuator stiffness, switch motion, and enclosure on real components first.

Build123d's [assembly guide](https://build123d.readthedocs.io/en/latest/how_to/assemblies.html) explains the named compound tree. Its [STEP import/export reference](https://build123d.readthedocs.io/en/stable/import_export.html) describes the interchange format used here.

## Checked-in candidate and independent CAD checks

The included STEP is the palm-facing Choc candidate: `headAcross=28`, `headShift=-2`, `offsetX=6`, `offsetY=-2`, `gap=0.8`, `sensorFlip=true`. Its pointer axis is workbench `(8, 66)` and CAD `(8, −66)` mm. The nearest thumb key center is **Lower, 22.266 mm** from that axis. The modeled right half remains 134.825 × 106.350 mm in plan; its bounding rectangle does not grow, but its carrier gains 258.135 mm² of local material. The 15.850 mm nominal assembled height is not an enclosure tolerance or fabrication specification.

The assembly contains 83 named solids: 11 nominal rigid bodies, 49 envelopes, and 23 reference bodies. The model’s **loaded parts and plug** should be viewed with envelopes on; the rigid-only filter deliberately omits the unmeasured internal population of the XIAO, purchased driver, and rubber cap instead of presenting them as precise CAD. This file represents the proposed right half, not a fabricated two-half keyboard.

Each row below is a minimum 3D distance measured on the **re-imported STEP**. All listed pairs have zero common solid volume in this state. A 0.6 mm nominal side gap, in particular, is not a tolerance or fastener-access allowance.

| Pair (STEP ids) | Separation, mm |
|---|---:|
| XIAO mounted allowance to full Lower keystroke (`xiao`, `sweep-19`) | 1.588075 |
| Cable plug approach to bridge (`plug`, `bridge`) | 3.040 |
| Cable plug approach to sensor board (`plug`, `sensor`) | 3.426675 |
| XIAO mounted allowance to bridge (`xiao`, `bridge`) | 0.800 |
| XIAO mounted allowance to sensor PCB (`xiao`, `sensor`) | 1.750 |
| Proposed bridge foot to controller (`foot-0`, `xiao`) | 0.600 |
| Sensor PCB to full Lower keystroke (`sensor`, `sweep-19`) | 5.646391 |

Reproduce the decisive pair and deliberately rejected alternative:

```sh
.venv-stack/bin/python mechanical/stack/assembly.py \
  --output /tmp/tapir-checked.step \
  --closest 'xiao,bridge,sensor,post,stick-cap,foot-*,sensor-face' 'sweep-*,switch-*' \
  --closest plug 'bridge,sensor,foot-*,switch-*,sweep-*,driver,battery'
.venv-stack/bin/python mechanical/stack/assembly.py \
  --options '{"orientation":"inner","offsetX":4,"offsetY":0,"gap":0.8,"headAcross":0,"headShift":9,"sensorFlip":true}' \
  --output /tmp/tapir-rejected.step --measure plug bridge
```

`--closest` finds the nearest actual solids among all matching re-imported IDs, using bounding boxes only to prune impossible candidates. The first check spans 420 possible stack-to-key pairs; the USB check spans 50. The deliberately rejected inward-facing alternative intersects the USB approach by **8.127 mm³**. This check uses the moving plug reserve, not merely the visible metal receptacle.

The default-source solid fingerprint (printed by the exporter) is `b2a21bc50fed99ccbcf73c6c7fbebc92983c2dc4d1bde2611d1a46f45154fb11`; a geometry or label revision will change it. The shipped STEP is AP214, 1,840,526 bytes, SHA-256 `82dcb751d7d4ee7719542c8d7be850bb0ca73faf9f46d3cc7f5c5b6d5b97ad39`.
