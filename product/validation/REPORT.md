# Tapir Rev A acceptance ledger

Disposition: **HOLD**. 70 PASS_DIGITAL, 1 BLOCKED, 9 PHYSICAL_PENDING. No physical test was performed or purchase authorized.

Digital and physical counts cannot be added into a meaningful “percent complete.” Every row is limited to the files, interface and kind of evidence named below. See [the rerun instructions](README.md), [machine-readable ledger and component inventory](results.json), and [manual first-article tests](BENCH.md).

## Stop conditions

- **charger.voltage-compatibility (BLOCKED)**: BQ25100 regulation can reach 4.23 V; pack specifies 4.20 V CC/CV, with no approved +30 mV charging window. A PCM overvoltage trip is NOT a permitted CV limit. Obtain written pack compatibility for the full tolerance or redesign the charger; USB-only testing with both cells disconnected. One good measured unit is not qualification.

## Evidence by domain

### Electrical

| Check | Disposition | Actual observation |
|---|---|---|
| `left.erc` | PASS_DIGITAL | KiCad 10.0.8; 0 findings incl warnings and exclusions; none; CLI exit 0 |
| `left.drc-parity` | PASS_DIGITAL | KiCad 10.0.8; 0 findings incl warnings and exclusions; none; CLI exit 0 |
| `left.schematic-endpoints` | PASS_DIGITAL | 114 functional pin/net endpoints on 51 electrical designators match independent matrix, power and controller contract |
| `left.pcb-endpoints` | PASS_DIGITAL | 114 functional pin/net endpoints on 51 electrical designators match independent matrix, power and controller contract |
| `left.endpoint-parity` | PASS_DIGITAL | 114 native XML ⇔ board endpoints agree; 445 copper segments/arcs, 27 vias; native DRC separately tests continuity |
| `right.erc` | PASS_DIGITAL | KiCad 10.0.8; 0 findings incl warnings and exclusions; none; CLI exit 0 |
| `right.drc-parity` | PASS_DIGITAL | KiCad 10.0.8; 0 findings incl warnings and exclusions; none; CLI exit 0 |
| `right.schematic-endpoints` | PASS_DIGITAL | 127 functional pin/net endpoints on 52 electrical designators match independent matrix, power and controller contract |
| `right.pcb-endpoints` | PASS_DIGITAL | 127 functional pin/net endpoints on 52 electrical designators match independent matrix, power and controller contract |
| `right.endpoint-parity` | PASS_DIGITAL | 127 native XML ⇔ board endpoints agree; 392 copper segments/arcs, 30 vias; native DRC separately tests continuity |
| `left.cam-readback` | PASS_DIGITAL | 23 source/output hashes matched; 9 nonempty Gerber layer functions and 69 PTH + 90 NPTH Excellon hits including vias match native board totals; max readback rounding ≤0.001 mm. Not a fabrication order. |
| `right.cam-readback` | PASS_DIGITAL | 23 source/output hashes matched; 9 nonempty Gerber layer functions and 77 PTH + 90 NPTH Excellon hits including vias match native board totals; max readback rounding ≤0.001 mm. Not a fabrication order. |

### Mechanical

| Check | Disposition | Actual observation |
|---|---|---|
| `left.carrier-contour` | PASS_DIGITAL | 15 native edges, 134.825 × 97.083 × 1.60 mm, 10716.82 mm²; bidirectional contour sample residual 0.000001 mm |
| `left.mount-registration` | PASS_DIGITAL | 4 native NPTHs vs boss datums; maximum XY 0.000000 mm, Ø 0.000000 mm. This does not establish printed boss fit. |
| `left.all-footprint-drills` | PASS_DIGITAL | 132/132 footprint drills one-to-one by owning reference, plating, coordinate and Ø; maximum XY 0.000001 mm, Ø 0.000000 mm. Includes switch, slide, mount and any wire-pad holes; routing vias excluded. |
| `left.switch-registration` | PASS_DIGITAL | 312 native XY/drill comparisons (including asymmetric Choc locators and backside diodes); max residual 0.000001 mm (SW19.locator-right XY); tolerance 0.015 mm |
| `left.cap-stroke` | PASS_DIGITAL | 378 pairwise convex prism checks across all 21 full-stroke unions (including rest and bottom-out); closest SW1-stroke to SW7-stroke: +0.500 mm; nominal, no tolerance or flex |
| `right.carrier-contour` | PASS_DIGITAL | 19 native edges, 134.825 × 106.350 × 1.60 mm, 11577.95 mm²; bidirectional contour sample residual 0.000000 mm |
| `right.mount-registration` | PASS_DIGITAL | 4 native NPTHs vs boss datums; maximum XY 0.000000 mm, Ø 0.000000 mm. This does not establish printed boss fit. |
| `right.all-footprint-drills` | PASS_DIGITAL | 137/137 footprint drills one-to-one by owning reference, plating, coordinate and Ø; maximum XY 0.000001 mm, Ø 0.000000 mm. Includes switch, slide, mount and any wire-pad holes; routing vias excluded. |
| `right.switch-registration` | PASS_DIGITAL | 294 native XY/drill comparisons (including asymmetric Choc locators and backside diodes); max residual 0.000001 mm (SW19.locator-right XY); tolerance 0.015 mm |
| `right.cap-stroke` | PASS_DIGITAL | 483 pairwise convex prism checks across all 21 full-stroke unions (including rest and bottom-out); closest SW1-stroke to SW7-stroke: +0.500 mm; nominal, no tolerance or flex |
| `left.boss-bore` | PASS_DIGITAL | 4 boss bores in actual tray mesh at z=−3.0; centers void, 16/16 annulus probes each; minimum center-to-wall radius 1.196 mm (nominal Ø2.4 case bores) |
| `left.tray-insertion` | PASS_DIGITAL | Vertical insertion/removal sweep: actual open tray mesh vs board outline + 152 switch-tail and backside-diode envelopes from seated heights to +25 mm; no material overlap. Other parts installed after board per assembly order. |
| `left.usb-bezel` | PASS_DIGITAL | 12.35 × 6.50 mm overmold prism, 38 mm straight approach from declared mouth, Z 0..6.50: no tray/bezel material in emitted meshes; seating datum/real overmold not validated. |
| `left.bezel-stroke` | PASS_DIGITAL | Entire 3 mm cap-travel envelope for 21 keys vs the actual emitted bezel mesh; zero material intersections across all overlapping Z slabs. |
| `left.pouch-to-case` | PASS_DIGITAL | 12.3 × 32 × 4.3 mm cell at drawing maximum vs actual tray, bezel and pouch organizer across all intersecting height slabs: no material intersection. Cell growth and the 105 mm lead/mate remain separate physical gates. |
| `left.lead-self-clearance` | PASS_DIGITAL | 105.000 mm path, 56 linear pieces; 0 nonlocal segment-pair overlaps in the assumed 2.20 mm XY × 1.20 mm Z wire reservation. Over all continuous points ≥6 mm apart along the wire and <1.20 mm apart in Z, minimum XY 4.669 mm (Z separation 0.000; arc lengths 13.567/19.567 mm). This tests the reserved volume, not actual conductor geometry, conductor strain, or the local 6 mm bend neighborhood. |
| `left.brep-motion` | PASS_DIGITAL | 44 required/reported checks; 36 common-volume screens, worst 0.0000139 mm³ (<0.00002); 4 swept-wire screens, worst 0.000000 mm³; independently summed lead centerline 105.000 mm; minimum modeled junction radius 1.166 mm (no vendor limit). 3 emitted meshes hash-match and current geometry hash. Seating/torque/cable flex not physically tested. |
| `left.engagement` | PASS_DIGITAL | 4 × M2×6 + 3 × M2×8; both nominally engage 1.60 mm nuts; tips clear desk by 0.8/1.3 mm. Physical torque, actual stock and pull-through remain open. |
| `left.carried-envelope` | PASS_DIGITAL | Modeled portable enclosure union 143.507 × 106.849 × 20.350 mm; CAD XYZ min (-107.136, -71.341, -6.8) and max (36.371, 35.508, 13.55). Includes 3 print meshes checked vs native finished BRep; transformed populated STEP model bounding boxes, 203 component/key/knob/slide envelopes and 7 head/nut locations. No stick cap on left. Optional feet not fitted; external cable excluded. Separately, nominal seated 36 mm Qualtek rigid overmold alone gives 143.507 × 134.831 mm XY; flexible cable extension, actual stop and bend are unqualified. Not a physical size. |
| `right.boss-bore` | PASS_DIGITAL | 4 boss bores in actual tray mesh at z=−3.0; centers void, 16/16 annulus probes each; minimum center-to-wall radius 1.196 mm (nominal Ø2.4 case bores) |
| `right.tray-insertion` | PASS_DIGITAL | Vertical insertion/removal sweep: actual open tray mesh vs board outline + 149 switch-tail and backside-diode envelopes from seated heights to +25 mm; no material overlap. Other parts installed after board per assembly order. |
| `right.usb-bezel` | PASS_DIGITAL | 12.35 × 6.50 mm overmold prism, 38 mm straight approach from declared mouth, Z 0..6.50: no tray/bezel material in emitted meshes; seating datum/real overmold not validated. |
| `right.bezel-stroke` | PASS_DIGITAL | Entire 3 mm cap-travel envelope for 21 keys vs the actual emitted bezel mesh; zero material intersections across all overlapping Z slabs. |
| `right.pouch-to-case` | PASS_DIGITAL | 12.3 × 32 × 4.3 mm cell at drawing maximum vs actual tray, bezel and pouch organizer across all intersecting height slabs: no material intersection. Cell growth and the 105 mm lead/mate remain separate physical gates. |
| `right.sensor-bores` | PASS_DIGITAL | 4 bridge-bore centers at sensor's 9.5 mm square drill coordinates; actual mesh in-plane radii 0.718..0.718 mm under nominal Ø1.80 sensor features. Not a screw/paste/bond specification; actual sensor retention unqualified. |
| `right.lead-self-clearance` | PASS_DIGITAL | 105.000 mm path, 111 linear pieces; 0 nonlocal segment-pair overlaps in the assumed 2.20 mm XY × 1.20 mm Z wire reservation. Over all continuous points ≥6 mm apart along the wire and <1.20 mm apart in Z, minimum XY 4.559 mm (Z separation 1.200; arc lengths 98.367/104.367 mm). This tests the reserved volume, not actual conductor geometry, conductor strain, or the local 6 mm bend neighborhood. |
| `right.brep-motion` | PASS_DIGITAL | 57 required/reported checks; 43 common-volume screens, worst 0.0000000 mm³ (<0.00002); 9 swept-wire screens, worst 0.000000 mm³; independently summed lead centerline 105.000 mm; minimum modeled junction radius 1.6 mm (no vendor limit). 4 emitted meshes hash-match and current geometry hash. Seating/torque/cable flex not physically tested. |
| `right.engagement` | PASS_DIGITAL | 4 × M2×6 + 3 × M2×8; both nominally engage 1.60 mm nuts; tips clear desk by 0.8/1.3 mm. Physical torque, actual stock and pull-through remain open. |
| `right.analog-harness-prints` | PASS_DIGITAL | Continuous 37.082 mm 3D provisional sensor→driver centerline with 2.80 mm XY diameter and 0.80 mm height vs every slab of 4 emitted prints. Closest in-plane material gap in intersecting Z slab: +0.285 mm to service-bezel on segment 4; 0 intersecting segment/slab pairs. Solder lands, terminals, flex and retention are provisional. |
| `right.carried-envelope` | PASS_DIGITAL | Modeled portable enclosure union 145.029 × 116.312 × 20.350 mm; CAD XYZ min (-38.578, -81.439, -6.8) and max (106.451, 34.873, 13.55). Includes 4 print meshes checked vs native finished BRep; transformed populated STEP model bounding boxes, 201 component/key/knob/slide envelopes and 7 head/nut locations. Right rubber stick-cap envelope tops at +11.05 mm and does not set maximum case height. Optional feet not fitted; external cable excluded. Separately, nominal seated 36 mm Qualtek rigid overmold alone gives 145.029 × 146.863 mm XY; flexible cable extension, actual stop and bend are unqualified. Not a physical size. |

### Power

| Check | Disposition | Actual observation |
|---|---|---|
| `left.cell-envelope` | PASS_DIGITAL | body 11.5×31.0×3.8 mm, reserve 13.5×33.0×4.8 vs max cell 12.3×32×4.3. Remaining total XYZ 1.20/1.00/0.50 mm is not approved swell/lead/insulation space. |
| `right.cell-envelope` | PASS_DIGITAL | body 11.5×31.0×3.8 mm, reserve 13.5×33.0×4.8 vs max cell 12.3×32×4.3. Remaining total XYZ 1.20/1.00/0.50 mm is not approved swell/lead/insulation space. |
| `charger.margin` | PASS_DIGITAL | Seeed Plus v1.1 schematic marks BQ25100, 2.7k ISET to GND + 2.7k to P0.13; high-Z application source. Conditional bound 47.30–54.25 mA (assumed ±1% R) below 100 mA; actively low could reach 108.49 mA. Bootloader/actual module not verified. |
| `power.week-budget` | PASS_DIGITAL | 100 mAh × 80% / 168 h = 0.476190 mA mean per half; 1 h pointer/7 h connected/16 h asleep. Arithmetic target only, not a runtime estimate. |
| `charger.voltage-compatibility` | BLOCKED | BQ25100 regulation can reach 4.23 V; pack specifies 4.20 V CC/CV, with no approved +30 mV charging window. A PCM overvoltage trip is NOT a permitted CV limit. Obtain written pack compatibility for the full tolerance or redesign the charger; USB-only testing with both cells disconnected. One good measured unit is not qualification. |
| `power.pointer-headroom` | PASS_DIGITAL | Lower-bound budget, not prediction: right driver alone draws 6.64 or 12.17 mAh/day for 1 h active + 7 h idle, assuming perfect gating 16 h. At Z-Tap-disabled typical idle that leaves 0.200 mA mean for both MCU/radio and all other right-half loads. Z-Tap-enabled idle alone would exceed the 11.43 mAh/day target. Host event suppression is not a measured sensor mode. |

### Integration

| Check | Disposition | Actual observation |
|---|---|---|
| `left.matrix-to-firmware` | PASS_DIGITAL | 24 physical positions traced from placed electrical pad through diode and controller to firmware slots; no aliases |
| `right.matrix-to-firmware` | PASS_DIGITAL | 21 physical positions traced from placed electrical pad through diode and controller to firmware slots; no aliases |
| `right.pointer-pins` | PASS_DIGITAL | 4/4 from board U1 pad through manufacturer v1.1 netlist into pin + polarity in right overlay; PS2_DATA=P1.15, PS2_CLK=P0.15, PS2_RST=P0.19, PTR_EN=P1.01 |
| `split.key-coverage` | PASS_DIGITAL | 45/45 global positions reached exactly once; 42 typing positions plus click, scroll, right-click at 42, 43, 44 |
| `left.part-variants` | PASS_DIGITAL | 51 footprint values matched to expected MPN/value; 3 XIAO/power/interface orientations and positions registered, worst XY 0.000000 mm |
| `left.step-placements` | PASS_DIGITAL | Independent AP214 parsing: native board plus 72 footprint model occurrences; every reference/model/count, signed side, yaw, Z and XY match the native board (max XY 0.00000000 mm). Each library STEP hash checked against the declared model fidelity; fabricated bores and bare harness pads are intentionally not separate STEP parts. |
| `left.populated-step-fit` | PASS_DIGITAL | All 73 native STEP occurrences (carrier + 72 modeled parts/caps), frame −1.595 mm, tested vs all printed bodies by the CAD kernel: no common-volume finding >0.00002 mm³. Independent AP214 membership/side/placement audit and STL section sweeps are separate. Solder fillets, cable flexibility, terminals and unmodeled internals are not tested by this BRep screen. |
| `right.part-variants` | PASS_DIGITAL | 52 footprint values matched to expected MPN/value; 4 XIAO/power/interface orientations and positions registered, worst XY 0.000000 mm |
| `right.step-placements` | PASS_DIGITAL | Independent AP214 parsing: native board plus 72 footprint model occurrences; every reference/model/count, signed side, yaw, Z and XY match the native board (max XY 0.00000000 mm). Each library STEP hash checked against the declared model fidelity; fabricated bores and bare harness pads are intentionally not separate STEP parts. |
| `right.populated-step-fit` | PASS_DIGITAL | All 73 native STEP occurrences (carrier + 72 modeled parts/caps), frame −1.595 mm, tested vs all printed bodies by the CAD kernel: no common-volume finding >0.00002 mm³. Independent AP214 membership/side/placement audit and STL section sweeps are separate. Solder fillets, cable flexibility, terminals and unmodeled internals are not tested by this BRep screen. |
| `controller.hidden-lands` | PASS_DIGITAL | 6/6 hidden host lands registered to Seeed module refs/nets; battery pads have 1.7812 × 1.0160 mm nominal bounding-rectangle overlap. No solder paste/reflow/yield proof. |

### Sourcing

| Check | Disposition | Actual observation |
|---|---|---|
| `left.inventory` | PASS_DIGITAL | 55 placed references, independently enumerated incl 51 electrical parts and 4 mechanical holes |
| `right.inventory` | PASS_DIGITAL | 56 placed references, independently enumerated incl 52 electrical parts and 4 mechanical holes |
| `bom.placement-accounting` | PASS_DIGITAL | 28 unique BOM lines; 102 purchased on-carrier references mapped to a unique line by side and quantity (excludes bare pads and drilled holes). Off-board items retained separately. |

### Firmware

| Check | Disposition | Actual observation |
|---|---|---|
| `keymap.original-42` | PASS_DIGITAL | 126/126 original bindings match normalized frozen keymap SHA on Base/Lower/Raise; 3 appended controls match, none silently trigger original hold-taps |
| `left.uf2` | PASS_DIGITAL | nRF52840 UF2 670 validated block numbers/family/magic, 171520 payload bytes, addresses 0x27000..0x50e00 exclusive; not a flash or HID trial |
| `right.uf2` | PASS_DIGITAL | nRF52840 UF2 999 validated block numbers/family/magic, 255744 payload bytes, addresses 0x27000..0x65700 exclusive; not a flash or HID trial |
| `firmware.distinct` | PASS_DIGITAL | Both UF2 digests are different (build configs/roles checked separately) |
| `left.compiled-role` | PASS_DIGITAL | Resolved left role, 45 transform cells, 10 row/column GPIOs and wake flags; sleep enabled at 900000 ms and P0.13 compiled as no-pull input; image execution on hardware pending |
| `right.compiled-role` | PASS_DIGITAL | Resolved right role, 45 transform cells, 10 row/column GPIOs and wake flags; sleep enabled at 900000 ms and P0.13 compiled as no-pull input; image execution on hardware pending |
| `firmware.pointer-events` | PASS_DIGITAL | 12 observed ZMK native events match independent sequence: motion, left held during drag, release, wheel on both axes, return to cursor, right held then release. This did not exercise real PS/2, split BLE, USB or hardware wake. |
| `firmware.split-ble-hog` | PASS_DIGITAL | Independent byte-level decode of 13 × 9-byte mouse reports on paired, subscribed third simulated host: opposing-hand left/right drag and releases, two isolated wheel axes, cursor restored; real RF, plug, PS/2 transducer and abrupt disconnect are untested. |
| `firmware.evidence-freeze` | PASS_DIGITAL | 12 listed build/test/vendor evidence digests verified, including both handed UF2s, resolved DTS/Kconfigs and actual simulation traces. The build procedure and clean replay record are supplied; digest checks alone do not certify physical execution. |

### Physical

| Check | Disposition | Actual observation |
|---|---|---|
| `physical.mounts` | PHYSICAL_PENDING | M01/M03: actual bores, fastener/tool access, bridge load/retention and removal are unmeasured. |
| `physical.stroke` | PHYSICAL_PENDING | M02/M06: 42 physical switches + caps, 3 buttons, thumb reach and simultaneous presses not exercised. |
| `physical.usb` | PHYSICAL_PENDING | M04: no actual USB overmold, mating stop or closed-case cable measured on either half. |
| `physical.pouch` | PHYSICAL_PENDING | M05: actual maximum pouch/PCM/wires, swelling, insulation and safe closure unverified. |
| `physical.polarity` | PHYSICAL_PENDING | E01/E02: board J1 pin allocation is intent. Exact Adafruit 1570 drawing calls for a reversed plug; verify real pack polarity with meter before connecting, never infer from colors. |
| `physical.charge` | PHYSICAL_PENDING | E02: physical 50 mA mode and peak below 100 mA through reset, DFU, USB hot-plug, suspend and charge termination not measured. |
| `physical.power` | PHYSICAL_PENDING | E03/E04: rail startup and backfeed, both battery-only current integrals, sleep/wake and seven-day runtime not measured. |
| `physical.rf` | PHYSICAL_PENDING | E05: closed-case BLE range/reconnect, hand attenuation and loss under load unmeasured. |
| `physical.hid` | PHYSICAL_PENDING | H01–H04: real host USB/BLE, cross-half drag and scroll, disconnects and recovery not exercised. |

## Physical-key circuit trace

| Hand | Ref | Legend | XY (mm) | Row/column GPIO | Global matrix | Keymap index |
|---|---|---|---|---|---|---|
| left | SW1 | Esc | -90.00, -9.00 | D0/D4 | 0,0 | 0 |
| left | SW2 | Q | -72.00, -13.00 | D0/D5 | 0,1 | 1 |
| left | SW3 | W | -54.00, -17.00 | D0/D6 | 0,2 | 2 |
| left | SW4 | E | -36.00, -20.00 | D0/D7 | 0,3 | 3 |
| left | SW5 | R | -18.00, -17.00 | D0/D8 | 0,4 | 4 |
| left | SW6 | T | 0.00, -15.50 | D0/D9 | 0,5 | 5 |
| left | SW7 | Shift | -90.00, 8.00 | D1/D4 | 1,0 | 12 |
| left | SW8 | A | -72.00, 4.00 | D1/D5 | 1,1 | 13 |
| left | SW9 | S | -54.00, 0.00 | D1/D6 | 1,2 | 14 |
| left | SW10 | D | -36.00, -3.00 | D1/D7 | 1,3 | 15 |
| left | SW11 | F | -18.00, 0.00 | D1/D8 | 1,4 | 16 |
| left | SW12 | G | 0.00, 1.50 | D1/D9 | 1,5 | 17 |
| left | SW13 | Ctrl | -90.00, 25.00 | D2/D4 | 2,0 | 24 |
| left | SW14 | Z | -72.00, 21.00 | D2/D5 | 2,1 | 25 |
| left | SW15 | X | -54.00, 17.00 | D2/D6 | 2,2 | 26 |
| left | SW16 | C | -36.00, 14.00 | D2/D7 | 2,3 | 27 |
| left | SW17 | V | -18.00, 17.00 | D2/D8 | 2,4 | 28 |
| left | SW18 | B | 0.00, 18.50 | D2/D9 | 2,5 | 29 |
| left | SW19 | Alt | -21.00, 41.00 | D3/D7 | 3,3 | 36 |
| left | SW20 | Raise | -0.60, 45.00 | D3/D8 | 3,4 | 37 |
| left | SW21 | Space | 20.00, 53.00 | D3/D9 | 3,5 | 38 |
| left | SW22 | L | -22.00, 57.00 | D3/D4 | 3,0 | 42 |
| left | SW23 | Scroll | -33.00, 57.00 | D3/D5 | 3,1 | 43 |
| left | SW24 | R | -44.00, 57.00 | D3/D6 | 3,2 | 44 |
| right | SW6 | Y | 0.00, -15.50 | D0/D9 | 0,6 | 6 |
| right | SW5 | U | 18.00, -17.00 | D0/D8 | 0,7 | 7 |
| right | SW4 | I | 36.00, -20.00 | D0/D7 | 0,8 | 8 |
| right | SW3 | O | 54.00, -17.00 | D0/D6 | 0,9 | 9 |
| right | SW2 | P | 72.00, -13.00 | D0/D5 | 0,10 | 10 |
| right | SW1 | \ | 90.00, -9.00 | D0/D4 | 0,11 | 11 |
| right | SW12 | H | 0.00, 1.50 | D1/D9 | 1,6 | 18 |
| right | SW11 | J | 18.00, 0.00 | D1/D8 | 1,7 | 19 |
| right | SW10 | K | 36.00, -3.00 | D1/D7 | 1,8 | 20 |
| right | SW9 | L | 54.00, 0.00 | D1/D6 | 1,9 | 21 |
| right | SW8 | ; | 72.00, 4.00 | D1/D5 | 1,10 | 22 |
| right | SW7 | ' | 90.00, 8.00 | D1/D4 | 1,11 | 23 |
| right | SW18 | N | 0.00, 18.50 | D2/D9 | 2,6 | 30 |
| right | SW17 | M | 18.00, 17.00 | D2/D8 | 2,7 | 31 |
| right | SW16 | , | 36.00, 14.00 | D2/D7 | 2,8 | 32 |
| right | SW15 | . | 54.00, 17.00 | D2/D6 | 2,9 | 33 |
| right | SW14 | / | 72.00, 21.00 | D2/D5 | 2,10 | 34 |
| right | SW13 | Enter | 90.00, 25.00 | D2/D4 | 2,11 | 35 |
| right | SW21 | Bksp | -20.00, 53.00 | D3/D9 | 3,6 | 39 |
| right | SW20 | Lower | 0.60, 45.00 | D3/D8 | 3,7 | 40 |
| right | SW19 | Tab | 21.00, 41.00 | D3/D7 | 3,8 | 41 |

## Component traveller

The physical column does not change because CAD models loaded or ERC passed. Grouped non-PCB items show the installed quantity per side; carrier references are one row per placed instance.

| Hand | Designator / item | Value / identity | Qty | Electrical evidence | BOM line | Model/fit scope and limits | Physical |
|---|---|---|---:|---|---|---|---|
| left | D1 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D10 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D11 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D12 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D13 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D14 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D15 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D16 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D17 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D18 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D19 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D2 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D20 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D21 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D22 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D23 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D24 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D3 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D4 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D5 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D6 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D7 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D8 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | D9 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| left | H1 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| left | H2 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| left | H3 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| left | H4 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| left | J1 | S2B-PH-SM4-TB(LF)(SN) | 1 | PASS_DIGITAL | J1 | JST_S2B_PH_SM4_TB_fit.step: Original simplified JST PH side-entry surface-mount 2-position fit body from drawing; no latch/insertion-force validation | PHYSICAL_PENDING |
| left | S1 | PCM12SMTR | 1 | PASS_DIGITAL | S1 | SW_SPDT_PCM12.step: KiCad native; original model header explicitly identifies PCM12SMTR | PHYSICAL_PENDING |
| left | SW1 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW10 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW11 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW12 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW13 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW14 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW15 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW16 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW17 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW18 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW19 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW2 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW20 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW21 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW22 | PTS810SJM250SMTR LFS | 1 | PASS_DIGITAL | MS | SW_SPST_PTS810.step: PTS810 J-bend series; 2.50 mm height verified, actuator grade/force not modeled | PHYSICAL_PENDING |
| left | SW23 | PTS810SJM250SMTR LFS | 1 | PASS_DIGITAL | MS | SW_SPST_PTS810.step: PTS810 J-bend series; 2.50 mm height verified, actuator grade/force not modeled | PHYSICAL_PENDING |
| left | SW24 | PTS810SJM250SMTR LFS | 1 | PASS_DIGITAL | MS | SW_SPST_PTS810.step: PTS810 J-bend series; 2.50 mm height verified, actuator grade/force not modeled | PHYSICAL_PENDING |
| left | SW3 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW4 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW5 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW6 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW7 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW8 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | SW9 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| left | U1 | XIAO nRF52840 Plus | 1 | PASS_DIGITAL | U1 | XIAO_nRF52840_Plus_nonSense_fit.step: Independently constructed from non-Sense Plus v1.1 artwork; 23 edge positions, 14 header holes, no IMU/microphone; Z allowances | PHYSICAL_PENDING |
| right | C1 | 1uF | 1 | PASS_DIGITAL | C1 | C_0603_1608Metric.step: package only; thickness depends on actual selected capacitor | PHYSICAL_PENDING |
| right | C2 | 100nF | 1 | PASS_DIGITAL | C2 | C_0603_1608Metric.step: package only; thickness depends on actual selected capacitor | PHYSICAL_PENDING |
| right | D1 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D10 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D11 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D12 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D13 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D14 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D15 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D16 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D17 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D18 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D19 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D2 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D20 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D21 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D3 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D4 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D5 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D6 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D7 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D8 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | D9 | 1N4148WS-7-F | 1 | PASS_DIGITAL | D | D_SOD-323.step: SOD-323 package CAD, not die-specific | PHYSICAL_PENDING |
| right | H1 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| right | H2 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| right | H3 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| right | H4 | M2_Carrier_Mount | 1 | NOT_APPLICABLE | fabricated feature | Fabricated hole in carrier; no separate purchased solid. | PHYSICAL_PENDING |
| right | J1 | S2B-PH-SM4-TB(LF)(SN) | 1 | PASS_DIGITAL | J1 | JST_S2B_PH_SM4_TB_fit.step: Original simplified JST PH side-entry surface-mount 2-position fit body from drawing; no latch/insertion-force validation | PHYSICAL_PENDING |
| right | J2 | SK8707-01-004 host cable | 1 | PASS_DIGITAL | fabricated feature | Bare copper harness pads; no connector solid. Actual interconnect, strain relief and solder are bench-only. | PHYSICAL_PENDING |
| right | R1 | 4.7k | 1 | PASS_DIGITAL | R12 | R_0603_1608Metric.step: package only; suffix/value does not follow from body geometry | PHYSICAL_PENDING |
| right | R2 | 4.7k | 1 | PASS_DIGITAL | R12 | R_0603_1608Metric.step: package only; suffix/value does not follow from body geometry | PHYSICAL_PENDING |
| right | R3 | 100k | 1 | PASS_DIGITAL | R3 | R_0603_1608Metric.step: package only; suffix/value does not follow from body geometry | PHYSICAL_PENDING |
| right | S1 | PCM12SMTR | 1 | PASS_DIGITAL | S1 | SW_SPDT_PCM12.step: KiCad native; original model header explicitly identifies PCM12SMTR | PHYSICAL_PENDING |
| right | SW1 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW10 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW11 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW12 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW13 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW14 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW15 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW16 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW17 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW18 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW19 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW2 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW20 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW21 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW3 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW4 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW5 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW6 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW7 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW8 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | SW9 | CPG135001D01 | 1 | PASS_DIGITAL | SW | SW_Kailh_Choc_V1.step: KiSwitch Choc v1 family mounting/outer geometry verified against target; not supplier-certified SKU; spring, switch force and stem color not indicative; MBK_1U_clearance_seated.step: Independent seated keycap envelope; excludes stem prongs, not mold/print geometry | PHYSICAL_PENDING |
| right | U1 | XIAO nRF52840 Plus | 1 | PASS_DIGITAL | U1 | XIAO_nRF52840_Plus_nonSense_fit.step: Independently constructed from non-Sense Plus v1.1 artwork; 23 edge positions, 14 header holes, no IMU/microphone; Z allowances | PHYSICAL_PENDING |
| right | U2 | TPS22918DBVR | 1 | PASS_DIGITAL | U2 | SOT-23-6.step: nominal six-terminal SOT-23/DBV package, not a TI assembly model | PHYSICAL_PENDING |
| left | CAP | KC10130_1U-BK | 21 | NOT_APPLICABLE | CAP | Per-switch MBK envelope installed on every switch in carrier STEP and full cap-stroke screen; not an original supplier BRep. | PHYSICAL_PENDING |
| right | CAP | KC10130_1U-BK | 21 | NOT_APPLICABLE | CAP | Per-switch MBK envelope installed on every switch in carrier STEP and full cap-stroke screen; not an original supplier BRep. | PHYSICAL_PENDING |
| left | BT | 1570 | 1 | NOT_APPLICABLE | BT | Maximum-pack envelope, printed pocket and 105 mm nominal lead routing; no actual pouch, heat, strain or polarity validation. | PHYSICAL_PENDING |
| right | BT | 1570 | 1 | NOT_APPLICABLE | BT | Maximum-pack envelope, printed pocket and 105 mm nominal lead routing; no actual pouch, heat, strain or polarity validation. | PHYSICAL_PENDING |
| right | TPK | SK8707-01-004 | 1 | NOT_APPLICABLE | TPK | Kit parent line, not an extra installed part. See sensor, driver, dome and wire evidence. | PHYSICAL_PENDING |
| right | TPSEN | SK8707-01-004 / sensor child | 1 | NOT_APPLICABLE | TPSEN | Sensor dimensions, four registered bores and provisional attachment land; actual strain element/adhesive not qualified. | PHYSICAL_PENDING |
| right | TPDRV | SK8707-01-004 / driver child | 1 | NOT_APPLICABLE | TPDRV | Detached driver envelope/cover motion and electrical pin contract; actual terminations, retention and solder fillets unmodeled. | PHYSICAL_PENDING |
| right | TPDOM | SK8707-01-004 / included dome | 1 | NOT_APPLICABLE | TPDOM | Installed dome and post envelope; force, full deflection, rubber geometry and subjective reach require a physical sample. | PHYSICAL_PENDING |
| right | WA | 4736 | 4 | NOT_APPLICABLE | WA | Four analog node assignments documented; lead clearances, strain relief, analog balance, soldering and actual function require assembly. | PHYSICAL_PENDING |
| right | WD | 4736 | 5 | NOT_APPLICABLE | WD | Five host pad/node assignments documented; soldering, insulation, strain relief and signal integrity require assembly. | PHYSICAL_PENDING |
| left | F6 | HBS73801-M2-6-A2 | 4 | NOT_APPLICABLE | F6 | Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested. | PHYSICAL_PENDING |
| right | F6 | HBS73801-M2-6-A2 | 4 | NOT_APPLICABLE | F6 | Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested. | PHYSICAL_PENDING |
| left | F8 | HBS73801-M2-8-A2 | 3 | NOT_APPLICABLE | F8 | Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested. | PHYSICAL_PENDING |
| right | F8 | HBS73801-M2-8-A2 | 3 | NOT_APPLICABLE | F8 | Native smooth shaft/head/pocket and drive access screen; actual threaded engagement/torque untested. | PHYSICAL_PENDING |
| left | FN | NXM02A2 | 7 | NOT_APPLICABLE | FN | Native M2 AF4 envelope, pocket, full axial engagement; nut retention/tolerance untested. | PHYSICAL_PENDING |
| right | FN | NXM02A2 | 7 | NOT_APPLICABLE | FN | Native M2 AF4 envelope, pocket, full axial engagement; nut retention/tolerance untested. | PHYSICAL_PENDING |
| left | PCBA | Tapir Rev A left | 1 | NOT_APPLICABLE | PCBA | Native outline, mounting drill, CAM, seated populated BRep and continuous as-soldered tray sweep. | PHYSICAL_PENDING |
| right | PCBB | Tapir Rev A right | 1 | NOT_APPLICABLE | PCBB | Native outline, mounting drill, CAM, seated populated BRep and continuous as-soldered tray sweep. | PHYSICAL_PENDING |
| left | CASETRAY | bottom_tray L/R | 1 | NOT_APPLICABLE | CASETRAY | Native pan vs emitted STL; bores, board/solder field, floor, wall and service sweeps checked at nominal pose. | PHYSICAL_PENDING |
| right | CASETRAY | bottom_tray L/R | 1 | NOT_APPLICABLE | CASETRAY | Native pan vs emitted STL; bores, board/solder field, floor, wall and service sweeps checked at nominal pose. | PHYSICAL_PENDING |
| left | CASEBEZ | service_bezel_and_hood L/R | 1 | NOT_APPLICABLE | CASEBEZ | Native upper bezel vs emitted STL; cap stroke, release/screwdriver/USB paths and paddle regions checked at nominal pose. | PHYSICAL_PENDING |
| right | CASEBEZ | service_bezel_and_hood L/R | 1 | NOT_APPLICABLE | CASEBEZ | Native upper bezel vs emitted STL; cap stroke, release/screwdriver/USB paths and paddle regions checked at nominal pose. | PHYSICAL_PENDING |
| left | CASECASS | pouch_separator_and_winding_form L/R | 1 | NOT_APPLICABLE | CASECASS | Seated and descending cassette checked against case and maximum pouch; numerical uncut cable path, no cell was fitted. | PHYSICAL_PENDING |
| right | CASECASS | pouch_separator_and_winding_form L/R | 1 | NOT_APPLICABLE | CASECASS | Seated and descending cassette checked against case and maximum pouch; numerical uncut cable path, no cell was fitted. | PHYSICAL_PENDING |
| right | BRIDGE | captive_pointer_bridge R | 1 | NOT_APPLICABLE | BRIDGE | Native low tabs, feet, controller/USB envelope and lift obstruction; emitted sensor pilot bores; load and attachment untested. | PHYSICAL_PENDING |
