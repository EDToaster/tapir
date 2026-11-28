# TMR half design journal

What was decided on the way to the rev A test coupon, what went wrong, and how each problem was solved. It is written as a reference for the 28-key board, so each section ends with what to carry over.

This file tells the story. The authoritative records stay where they were:

- [design-decisions.md](design-decisions.md): the decision log with status and evidence
- [analog-readout.md](analog-readout.md): the readout reasoning and arithmetic
- [coupon/README.md](coupon/README.md): the coupon's circuit, layout, ordering steps and test plan

State when this was written (2026-11-27): the coupon is designed and has been through one independent review and one round of fixes (commit `627ae98`). A second review of the fixes was still running. Nothing has been ordered, built or measured, so every electrical and magnetic number here is a **drawing** value or an estimate unless it says otherwise.

## Decisions at a glance

| Area | Choice | Status | Why, in one line |
| --- | --- | --- | --- |
| Layout | 6 × 5 grid, 28 keys (D1) | Decided | Half-size board leaves desk room for the mouse |
| Connection | Wired USB first, battery kept possible (D2) | Decided | Always-powered analog sensors make long battery life hard |
| Controller | nice!nano v2 clone, nRF52840 (D3) | Decided | Already owned |
| Switch | Gateron Low Profile Magnetic Jade Pro, KS-33D (D4) | Decided | MX-style stem, low profile, same switch as Partial-Gauss |
| Sensor placement | 4.40 mm south of the switch centre, bottom side (D5) | Decided | Partial-Gauss footprint; lies inside Gateron's sensor zone |
| Sensor | MDT TMR2617S-AAC-0.500-500, SOT-23-3 (D6) | Decided | Factory calibrated, so no programming order; about 20× less current than Hall |
| Readout | Two CD74HC4067SM96 16:1 muxes, shared select lines, one ADC pin each (D7) | Proposed | Only three analog pins are free; the ADC draws no steady current so a cheap mux is enough |
| Firmware | ZMK on the coupon, then Rust (embassy) with WebUSB settings (D8) | Decided | ZMK gets the coupon scanning without new code; Rust fixes reflash-to-change-threshold |
| Sensor power | Switched rail, firmware decides whether to pulse (D9) | Proposed | Cheap, keeps the battery option open |
| Test coupon | 2 × 3 keys before the full board (D10) | Proposed | Field strength, settling, noise and pulsing are all unmeasured |
| Test firmware | Small bare-metal program for timing tests (D11) | Proposed | ZMK cannot do microsecond delays or drive the rail pins |
| Thickness | Compare 1.2 mm and 1.6 mm coupons (D12) | Proposed | Gateron's drawing uses 1.2 mm; Partial-Gauss used 1.6 mm |
| Battery input | Series P-FET, reversed-polarity LED, 300 mA slide switch (D13, D15) | Proposed | Found in review, see [Battery path](#battery-path) |
| Rail control pins | P0 pins on the full board (D14) | Proposed | P1.04 is a low-frequency-only pin |
| Mux channel order | Grounded inputs between live keys on the coupon (D16) | Proposed | Lets the route keep analog and address lines apart |

## Sensor and magnetics

**A sensor that does not need programming.** Most linear TMR parts are programmed to order. The TMR2617S-AAC-0.500-500 is a stock build with its sensitivity (0.5 mV/V/Gs) and offset (50 % of VCC) set at the factory, and its SOT-23-3 pinout (1 VCC, 2 OUT, 3 GND) matches the Hall sensor Partial-Gauss used ([MDT datasheet](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf), **drawing**). The 0.75 build would give more signal but clips near 600 Gs.

**Board thickness was decided on a wrong statement.** D5 originally said Partial-Gauss was the only placement with a published field figure, so the board was fixed at 1.6 mm. The reviewer read the [Gateron KS-33D drawing, p. 7](https://www.gateron.com/u_file/2603/10/file/GATERONLowProfileMagneticJadeProSwitch-KS-33DD10B060NW-D276.pdf) and found the vendor's own reference: sensor under a 1.20 mm board, 75 ± 10 Gs at rest and 680 ± 70 Gs bottomed. Partial-Gauss reports about 400 G through 1.6 mm with a different sensor and no rest reading. The fix was to correct D5's evidence, keep the placement, and make thickness a question the coupon answers (order both, compare in T1).

- The worst case of 750 Gs still fits: the 0.500-500 build swings 45 % of VCC either side of mid-scale, which is about 900 Gs, leaving roughly 150 Gs.
- The two published figures cannot be divided to predict a gain. They come from different sensors and stacks. Travel swing at 1.2 mm is 680 − 75 = 605 Gs nominal, about 1.0 V at 3.3 V.
- JLCPCB quotes ±10 % on board thickness, so measure each board with calipers rather than trusting the nominal.
- The datasheet's transfer curve slopes down as its signed field rises. Record the actual output direction on hardware and work in magnitudes until then.

**Sensor stock is the long pole.** JLCPCB showed zero stock with a minimum buy of 18, and LCSC showed zero, on 2026-11-27. The sensor pads were lengthened on the outer row (0.55 mm of toe) so hand soldering is realistic; the row next to the Ø5.2 hole stays at 0.20 mm because of hole clearance.

**No plate.** The switch has no pins. It is held by a centre post and two pegs, and Gateron's drawing expects a 1.2 mm plate. On the coupon the switches can tilt, which changes magnet height and shows up as noise.

Carry over to the 28-key board:

- Choose thickness from the coupon's T1 result, then confirm the sensor variant (0.500 or 0.75).
- Order sensors into the JLCPCB parts library before anything else; 28 keys plus spares.
- Design the plate with the board. Use brass or nylon M2 hardware near the magnets and keep steel connector shells away from the outer keys.

## Readout and timing

**Why a cheap mux works.** The nRF52840 ADC only charges a small sampling capacitor, and Nordic lists 3 µs acquisition as enough for sources up to 10 kΩ ([SAADC](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/saadc.html), **drawing**). A few hundred ohms of switch resistance gives a time constant near 18 ns. The open question is how fast the sensor's own output stage recovers when it is connected to a node still holding the previous key's voltage. Neither mux datasheet gives on-resistance at 3.3 V, so the ADG706 stays as a fallback.

**The settling test did not test anything.** The first test plan read a grounded mux input next to a pressed key. A grounded input is a 0 Ω source and settles almost instantly, so the test could only pass. It also told the owner to sweep a ZMK delay that is a kernel sleep and cannot do single microseconds. The rewritten T3 alternates between two live sensors at different levels and between a key and ground, in both directions, with a busy-wait delay. That needs the small bare-metal program in D11.

**Scan-time figures are floors.** Sixteen addresses with two sequential conversions each give 192 µs at a 2 µs wait and 480 µs at 20 µs, and 704 µs with the 10 µs acquisition used in the ZMK sketch. These leave out driver overhead and averaging. The sensor's datasheet noise (up to 10 mVpp at 3.3 V, about 12 counts) may force averaging, which costs scan time.

**"Ratiometric" was assumed.** The ADC full scale follows the nRF's VDD. The sensors run from a switched rail behind a FET and a shunt, and on clones the VCC pin can come from a separate regulator. The documented method is now to read the rail monitor through the same mux and compute `(key − ground) / (2 × (MON − ground))`, with T7 checking it on USB and battery.

Carry over:

- With 28 keys on 32 channels there are only four spare inputs, so the coupon's grounded-neighbour arrangement cannot be repeated. Recheck settling with a fully populated mux.
- Keep one rail-monitor channel and at least one grounded channel per mux.
- Keep the unpopulated series resistor and capacitor pads at each ADC input.

## Sensor power

**Pulsing can cost more than leaving the sensors on.** Each sensor draws up to 300 µA, so 28 draw up to 8.4 mA. Every pulse also refills each 100 nF bypass capacitor. At 1 kHz the estimate is 11.7 mA pulsed against 8.4 mA always on; pulsing only wins at low rates (0.23 mA at 20 Hz) or with smaller capacitors. The coupon has one rail with 100 nF and one with 10 nF to measure the noise cost.

**The rail monitor cannot show sensor readiness.** The monitor and the rail settle within a few microseconds, while the sensor needs up to 100 µs after power-on. T6 now reads a key address at stepped delays after switch-on.

**Back-powering.** If the address lines stay high while a rail or the 3.3 V supply is off, the muxes are fed through their input clamps. The firmware rule is to stop sampling and drive S0 to S3 low before switching anything off.

**Pin choice.** Rail B's switch sits on P1.04, which Nordic lists as standard drive, low-frequency only. It is fine at coupon rates. P0.13 high enables the external 3.3 V output on a genuine nice!nano v2; one document had this backwards.

Carry over: use P0 pins for rail control, size the rail switch for 28 × 100 nF of inrush, and decide the pulsing policy from T6.

## Battery path

Three problems were found in a circuit that looked too simple to get wrong: connector, slide switch, B+.

- **Switch rating.** The MSK12C02 is rated 50 mA and the module charges at about 100 mA (300 to 500 mA with the boost jumper). It was replaced with the C&K PCM12SMTR, rated 300 mA at 6 V DC. Leave the boost jumper open.
- **Reversed pack.** JST-PH packs are sold in both polarities. A series AO3401A (drain to the connector, gate to ground through 100 kΩ) now blocks a reversed pack on battery alone, and the off position of the switch isolates the module.
- **The case the FET does not cover.** With USB connected and the switch on, the module's charger raises B+, which can turn the FET on against a reversed pack. No safe current can be claimed for that. An LED on the raw battery node lights only when the pack is reversed, with the switch off, before anything reaches the module. The first-connection procedure is: switch off, plug in, LED dark, confirm with a meter, switch on.

Carry over: keep all three on the full board, and consider a protection scheme that also covers the USB-present case if the board will be used on battery often.

## Layout

**The autorouter put the analog signals beside the address lines.** The first route had the mux outputs running up to 42.5 mm beside S2 at a 0.2 mm gap, ground on the opposite layer for about half of each analog net, and two ground pours joined by three vias. DRC passed because no rule described any of this. The board would have read keys, but the settling and crosstalk results would have included a layout artefact.

How it was fixed:

- A net class and custom rule give analog nets 0.5 mm clearance to the control and battery nets. KiCad's Specctra export does not carry custom rules, so the router has to be given them separately.
- Mux channels were reassigned so grounded inputs sit between live ones, which opened routing room at the mux pins.
- Stitching-via positions next to every sensor, bypass capacitor and mux ground pin were reserved before routing, then more were added after the pour was filled. The board went from 3 ground vias to 97.
- Redundant ground tracks were trimmed and a pad-free sliver of pour was removed. Every remaining pour region has at least two vias.
- A new gate, `check_analog.py`, measures all of this on the routed board and fails the build on regression.

Result: no analog net runs beside a control net on the same layer inside 0.5 mm, and the worst opposite-layer overlap is 2.9 mm. The 80 % opposite-layer ground target was met on three of ten analog nets. MUXA ended lower than before (47 % against 55 %). That trade was accepted because these are kHz-rate signals and the address-line coupling was the part that would have corrupted the settling test; the gate holds each net at its achieved figure and keeps the 80 % goal visible.

Smaller layout lessons:

- Rules set exactly at the achieved value leave no margin. Copper to unplated holes went from 0.25 to 0.30 mm.
- A 0.12 mm pour neck was tried to gain coverage and rejected. Fill minimum width stays at 0.20 mm.
- FreeRouting narrows tracks at small pads; restore class widths after import. Some cost settings make it stall with nets unrouted, so keep the candidate that is DRC-clean and improve from there.
- Three bottom-side fiducials were added. Silkscreen strokes are at least 0.15 mm wide and 0.3 mm from the edge.

Carry over:

- Start the 28-key layout with the analog net class, the stitching plan and the measuring gate in place from the first route.
- Place each mux so the address lines arrive on the opposite side from the common pin.
- Six keys on two layers could not reach the ground-reference target. Price a four-layer board with an inner ground plane for the full keyboard and check which thicknesses the fab offers for it before fixing thickness.

## Fabrication and assembly files

**Placement rotations were wrong for nine of twelve polarised parts.** The corrections came from a community table keyed by footprint name. The reviewer downloaded JLCPCB's library footprint for each LCSC part number and fitted its pads onto the board's pads. Both rail FETs, all six sensors and the battery connector were a quarter or half turn off. Rotations are now keyed by LCSC number, and `check_cpl.py` repeats the pad fit on every build (42 placements, worst error 0.22 mm). Reapplying the old table makes the gate fail, which shows it can.

Carry over: every new part number gets its library pads added to the fixture. JLCPCB's placement preview is still the final check before paying.

## Silkscreen pattern

The quadtree Truchet pattern is drawn as strokes. Trimming the strokes along their centre lines near pads left it in fragments. Converting strokes to filled polygons and using polygon operations worked: subtract inflated keepouts, remove slivers, drop small islands, close narrow channels. The review then found uneven ink under the switch bodies, between 7 and 22 mm² per key on a board built to compare keys, so the 14 × 14 mm switch seats are now kept clear. A Gerber read-back gate checks stroke width, edge distance and seats on the plotted artwork.

## Checks that could not fail

The first design passed every gate and still had a blocker. The review explained why, and each gate was strengthened:

| Gate | Weakness | Now |
| --- | --- | --- |
| ERC | Every pin was typed passive, so nothing could conflict | Real pin types and power flags; removing the flags produces four errors |
| Schematic check | Compared the schematic with the manifest that generated it | Also compares the manifest with a separate datasheet pin table (81 pins, with sources) |
| CAM read-back | Compared Gerbers with data exported from the same board | Independent parser plus absolute checks on the artwork |
| Silk check | Only looked at the decorative pattern | Reads every plotted stroke, the edge distance and the switch seats |
| Rotations | "Cannot be proven offline" | Pad-fit gate against the assembler's library |
| DRC | No rule for ground quality | `check_analog.py` and `check_mechanical.py` (courtyards, hole clearance, battery track width) |

The general lesson is to ask of every gate what fault it would catch, then inject that fault once and watch it fail.

The build is deterministic: fixed UUIDs, no timestamps in the Gerbers, and flat plots for the preview images. Two builds in a row leave the tree unchanged, which makes review diffs meaningful.

## How the review was run

- Review guidance was collected first: [azonenberg's sign-off checklists](https://github.com/azonenberg/pcb-checklist), [jvanderberg's board review skill](https://github.com/jvanderberg/kicad-skills), [roccoagain's schematic and layout review skills](https://github.com/roccoagain/kicad-agent-skills), [kicad-happy](https://github.com/aklofas/kicad-happy), [Jitter's checklist](https://jitter.nl/en/pcb-checklist/) and [Memfault's firmware-side checklist](https://interrupt.memfault.com/blog/schematic-review-checklist).
- A reviewer who had not designed the board worked read-only in its own clone, re-derived every pin map from the datasheets, measured the routed board with its own scripts and tagged each claim as measured, from a datasheet, or unverified.
- It found 1 blocker, 6 majors and 16 minors, and no wiring, pin-map or footprint error.
- A different engineer made the fixes, with each one needing a before and after number or a gate. The same reviewer then re-reviewed.

What made it useful: the reviewer was told where the designer felt least sure, was asked to treat passing gates as claims, and had to list what it did not check.

## Checklist for the 28-key board

1. Run the coupon tests first. T1 fixes thickness and sensor variant, T2 noise and averaging, T3 settling delay, T6 the pulsing policy, T7 the normalisation method.
2. Check the actual clone module: B+ pad, 3.3 V pin voltage and current, P0.13 behaviour, antenna position.
3. Reuse the generator chain and all gates. Add the new parts to the datasheet pin table and the placement-pad fixture.
4. Route with the analog net class, pre-seeded stitching and `check_analog.py` from the start. Decide two or four layers early.
5. Keep the reverse-polarity FET, the indicator LED and a switch rated above the charge current.
6. Put rail control on P0 pins, keep a rail monitor and a grounded channel on each mux, and keep the firmware rule for powering down.
7. Design the plate and case with the board, and keep steel away from the magnets.
8. Order sensors into the parts library before the boards.
9. Have the finished design reviewed by someone who did not draw it, before ordering.

## Still unmeasured

Field at the sensor at either thickness, output direction, mux behaviour at 3.3 V, sensor recovery time, noise, rail rise and inrush, the clone's regulator and charger, switch retention without a plate, battery life, and whether ZMK builds against the sketch in the coupon README.
