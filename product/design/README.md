# Tapir Rev A placement interface

Use `geometry.json` for **both** electrically distinct carrier outlines, centers, orientations, drill features and assembly keep-outs. The geometry generator takes the typing layout from `workbench/layout.js` and the selected offset thumb stack from `workbench/stack.js`. No controller is left at the old right-hand location. No sensor shaft hole is drilled in the main carrier. The four holes in the Sprintek sensor belong to that purchased daughterboard only.

## Regenerate and validate

From the repository root, using Node 20+:

```sh
(cd workbench && npm ci)
node product/design/generate-geometry.mjs
node product/design/generate-geometry.mjs --check
```

Generation is deterministic; `--check` compares the exact bytes of the checked-in JSON. Both modes exit nonzero on failed dimensional screens or ID/check drift. This model is an interface contract, not a claim that a fit has been tested with parts. For native PCB, case and release checks, see the separate `product/electronics`, `product/mechanical` and `product/validation` workstreams.

## Axes, IDs and layer meaning

- **Datum.** Both halves have their own local millimetre top view. X increases to the observer's right, Y toward the palm, Z up. Carrier top is Z 0, bottom −1.6. An angle `a` is positive clockwise on that XY page. Points and holes are already transformed and must not be mirrored again, including the asymmetric switch pin/locator on the left.
- **Outline and PCB.** `halves[hand].outline` is an unclosed list of XY vertices; join the last to the first. Internal holes live in `holes`: `drill` is finished concept bore diameter; for a PTH pad the `diameter` field is its land size, not the drill. Polygon coordinates round to 0.000001 mm for reproducibility, not manufacturing tolerance. Width/depth below are carrier bounds, excluding protruding USB, switch actuator, case and plugged cables. The case should use native populated board output when available and cross-check it against these vertices.
- **Switches and buttons.** `switches[].ref` is SW1–SW21. R0–R2 use C0 outer through C5 inner; R3/C3–C5 are outer/middle/inner thumbs. Three left-only controls SW22/SW23/SW24 use R3/C0–C2 for click/hold-scroll/right. Arrays retain the layout's inner-to-outer geometric order; map by `ref`, `row`, `col`, never array index. The direct-solder Choc P1 at local (+5, −3.8) and P2 at (0, −5.9), rear-facing on both halves, match the product footprint, not the rotated legacy underside illustration. The body and cap footprint are unchanged. Community [PG1350 pad geometry](https://raw.githubusercontent.com/daprice/keyswitches.pretty/master/SW_PG1350.kicad_mod) is rotated and locally renumbered to match the product schematic; verify the exact switch drawing and solder side before ordering.
- **Components and solids.** `components` exposes named hardware, nominal and maximum pouch bodies, connector land-origin/pads, actuator, plug approach and RF zones; the right also includes bridge/feet, Sprintek sensor/shaft/cap, remote driver, five host solder pads and six discrete rail parts. `solids` is the flat rendering/check list: `{id,role,label,kind,polygon,bottom,top}` with additional center/angle where relevant. XY polygons + Z intervals describe extrusions, not supplier STEP replacements. A populated-module reserve and its substrate/shell, key rest and swept volume, max/nominal/growth battery, actual fixes and reserved tools overlap by design. Do **not** boolean-union every solid, count reserves as hardware, duplicate material from `components` + `solids`, or test intentional overlaps as interferences.
- **Routing vs packaging.** A 12 × 8 mm budget contains the native right-side power/conditioning electronics. Their approximate package solids are supplied separately; exact land shapes, tracks, pads under the XIAO and copper exclusions remain the native KiCad board's responsibility. `wiring.sensorToDriver` is a proposed lead centerline with **unqualified terminal mapping/physical egress**, not a production flex, copper net, or bend allowance. The 4 analog head leads are distinct from J2's 5 digital/power host connections. Battery wiring provides selected endpoints, width, height and 105 mm length; `product/mechanical` owns the single actual centerline, organizer construction and cable-length fit test. Never infer its path from the shortest endpoint distance.

## Assembly interface and tolerances

| Item | Left | Right |
| --- | --- | --- |
| Carrier bounding box, mm | 134.825 × 97.083 | 134.825 × 106.350 |
| USB controller origin, orientation | (21.8, −15.5), 0°; toward rear | (15.695, 64), 180°; toward palm |
| Battery/J1 service | Pouch (22.8, 15.5); JST (−39.5, 38.8), 90°, insert from −X | Pouch (−22.8, 15.5); JST (−20, −18), 0°, insert from +Y |
| Battery switch S1 | (−6, 61.85), 4.7° | (−22, 73.75), 0° |
| M2 board fasteners H1/H2/H3/H4 | (−83,−19.5), (10.5,−2.5), (14.5,62), (−79,31.5) | (83,−19.5), (−10.5,−2.5), (−14.5,62), (79,31.5) |
| Thumb pointer | Three 4.2 × 3.2 mm mouse switches; optional 8 × 5 mm paddle allowance | Shaft (8,66), Lower key 22.27 mm away; bridge Z 5.8…6.6, sensor substrate 6.75…7.55, tip reserve +11.05 |

The four 2.20 mm NPTH board fasteners assume maximum Ø4 × 1.6 mm heads, Ø5.4 mm underside bosses and Ø4.4 mm screwdriver clearance with keycaps removed. They replace the workbench's old illustrative bonded pucks. Install the screws before the caps and remove interfering caps before service. Metal thread/insert engagement, assembly sequence, torque and coupon strength need physical validation; the shaft stack's external feet are not these casing screws.

The native [Seeed Plus board](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip) supplies USB shell plan, bare-board area, nominal substrate and antenna origin. USB/component Z and the 6 × 6 mm RF neighborhood are conservative design screens, not measured connector stack or RF performance. The [Sprintek mechanical drawing, p. 6](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6) supplies detached substrate, hole and post dimensions, not retained cap height or completed harness. [C&K's PCM drawing](https://www.littelfuse.com/assetdocs/littelfuse-ck-slide-pcm-series-datasheet?assetguid=d2f6a96c-7a9a-4c4e-a5aa-5fe3075dffe5) and the installed KiCad `SW_SPDT_PCM12` footprint are the references for S1. Its two Ø0.9 locating holes are included in carrier drills; conservative tail envelopes below the board cover unknown actual insertion depth.

The selected [Adafruit 1570](https://www.adafruit.com/product/1570) nominal pouch is 11.5 × 31 × 3.8 mm. The [PKCELL pack drawing, p. 5](https://cdn-shop.adafruit.com/product-files/1570/1570datasheet.pdf#page=5) gives up to **12.3 × 32 × 4.3 mm before lifetime swelling**. Treat these as different solids. Beyond the as-built max, the provisional 13.5 × 33 × 4.8 mm space reserves only 0.6 mm on each side, 0.5 mm at each end, and 0.5 mm overhead. Its adequacy is unqualified; a cell cannot be compressed into it. Shelves, wires, retention, charger current and polarity require their own gates. The JST plug approach is a 12 mm service reserve, not the exact supplier housing outline.

## Nominal quantitative checks

`halves[hand].checks` exports every tested value and the limiting pair. The following are the most useful release checks:

| Check | Left minimum | Right minimum |
| --- | ---: | ---: |
| Pairwise complete 3 mm key travel | 0.500 mm | 0.500 mm |
| Backside diode vs switch terminal/locator reserves | 0.394 mm | 0.394 mm |
| Screw head / driver / boss / outer edge, positive limiting gap | 0.773 mm | 0.773 mm |
| Installed XIAO and overhanging shell vs keys | 4.160 mm | 1.588 mm |
| USB plug approach vs surrounding hardware | 7.981 mm | 3.040 mm |
| JST insertion vs nearest hard/reserved geometry | 9.210 mm | 0.600 mm |
| As-produced maximum pouch vs front components and J1 service | 4.523 mm | 1.100 mm |
| Screened RF neighborhood vs projected stack metal | Not a stacked radio | 1.460 mm; not an RF pass |
| Proposed four-lead analog bundle vs populated hardware / carrier edge | Not present | 0.550 mm to bridge / ≥1.698 mm to carrier edge |

These are unsigned Euclidean separations between disjoint nominal extrusions (negative if overlapping), using the same signed-prism routine as the workbench. Screw checks also use exact distance to the carrier perimeter; circle envelopes for collision are conservatively circumscribed. When a screw head overlaps a key's XY silhouette, its real Z separation still counts; the separate tool check omits only removable caps, never the soldered switch. Unmodeled hardware, solder variability, actual insertion trajectory, PCB bow, printing tolerance, wet/aged cell size, retainer stiffness, centering, RF, handling, real pointing and all electrical behaviors must pass their independent checks. There is no blanket “all hardware fits” verdict.

The earlier direct descent crossed the bridge. The current 37.082 mm sensor-lead polyline starts at the proposed top solder edge (18.84, 66, 7.55), rises to Z 7.85, exits the bridge on its key-side at Y < 59.05, then descends toward the remote driver. The whole proposed 2.8 mm wide × 0.8 mm high bundle is bounded by 96 short guard prisms covering each segment continuously, not just a set of points. The enclosure bezel must consume this same `wiring.sensorToDriver.points` path. Its two endpoints are nominal termination regions: they do not establish pin identity, soldering access, safe bend radius, strand diameter, strain relief, physical cut length or pointer-noise performance.
