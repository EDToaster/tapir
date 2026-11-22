# Tapir pointing-stick sourcing

The Tapir workbench models the Sprintek SK8707-01-004 under the right thumb cluster by default. A ThinkPad T440 donor is worth sampling because [Dabao’s builder installed a thumb-operated assembly](https://github.com/justinmklam/dabao/blob/main/docs/build-guide.md), but it has not been selected, measured or fitted to Tapir. No Tapir fit clearance, shaft length, case height, or electrical budget currently applies to it.

## What the reference footprint establishes

Read the [Dabao sensor footprint](https://github.com/justinmklam/dabao/blob/main/pcb/library/Library.pretty/TPSensorModule.kicad_mod) in its own local coordinates, with the shaft opening at (0, 0). The following dimensions are on the host PCB, not measurements of a loose donor:

| Reference feature | Dimension in mm | What it establishes |
| --- | --- | --- |
| Circular opening on `Edge.Cuts` | Ø7.2 (radius 3.6) | The opening in the Dabao carrier, not the diameter of the post, rubber cap or sensor body. |
| Two mounting holes | Ø2.1 drills at (0, −9.5) and (0, +9.5) | Hole centers are 19.0 apart. The drawn 2.7 mm copper pads are not hole diameters; nothing here fixes screw thickness, length, or head clearance. |
| Irregular `F.CrtYd` polygon | X −7.7 to +11.6; Y −11.5 to +11.5 | A 19.3 × 23.0 bounding box around reserved layout space. It is asymmetric about the opening and is not the physical board outline, a carrier cutout, or a metal-plate drawing. |

The [Dabao build guide](https://github.com/justinmklam/dabao/blob/main/docs/build-guide.md) shows the sensor ribbon soldered on the underside, the separate controller wired on top, and a printed stem selected to fit. That demonstrates an assembly method for the builder’s sample, not a combined module of known thickness. The sensor plate, controller, flex path, post and cap all need separate envelopes. Do not copy those three PCB dimensions into Tapir as a validated donor, or re-use the Sprintek’s proposed 4 mm square opening.

## How to identify a candidate

- **Start from a traceable donor.** Prefer an intact, identifiable keyboard or module whose markings, photos and seller can be recorded. The [Dabao sourcing note](https://github.com/justinmklam/dabao/blob/main/docs/trackpoint-sourcing.md) names the AliExpress jiyunsheng Store, a replacement-keyboard seller, and describes asking for only the T440 TrackPoint assembly. This is a sourcing lead, not a live listing, verified FRU, interchangeable revision, price, or stock guarantee.
- **Ask for the complete pointing stick.** Suggested wording: “I need the keyboard pointing-stick sensor with its post, mounting plate, separate driver PCB and intact connecting flex. Please confirm these exact items, not just red caps, the palm-rest touchpad/trackpad, or an unrelated keyboard. Can you show the unit you would supply, front, back and side, next to a metric ruler, with the connector and all markings readable?” Ask separately whether a matching cap and retention hardware are included.
- **Request electrical identification.** Ask for the keyboard FRU, sensor and driver markings, connector pitch, contact-side orientation, pinout and supply/logic voltages for that particular revision. Do not assume a T440 listing, matched photograph, cable color or the Sprintek’s interface establishes a safe pinout. No supplier has been contacted or order placed for this study.

## Gate before changing the CAD or BOM

- **Measure the actual assembly.** From the shaft axis and a stated carrier face, record the plate/body outline, backing bulges, rest and loaded cap height, screw head/nut heights, hole spacing, controller outline and populated Z on both faces. Record the flex attachment, direction, safe bend and strain relief; keep scaled photos and the exact sample revision with the measurements.
- **Try the retention scheme.** Make an inexpensive mounting coupon with the measured dimensions. Test clearance to the carrier, back cover, fully pressed neighboring keys, wire route and solder tails. Verify that repeated pointing and pulling on the cap cannot rock the sensor, loosen its backing, or cause shaft rub, drift or damage.
- **Verify the electrical and sleep budget.** Once the supply and pinout are confirmed, bench-test using a current-limited supply; verify startup, reset and pointing, then measure active, idle, sleep and wake current at the battery with USB disconnected on the intended BLE split controller. Test reconnection and repeated sleep/wake; if power gating is needed, verify deterministic resume and no back-powering through signal lines. The builder’s [power caveat](https://github.com/justinmklam/dabao/blob/main/docs/trackpoint-sourcing.md) is a reason to measure, not a current specification.
- **Promote only with evidence.** Keep this donor out of the default geometry and fit reports until its part identity, retention, electrical behavior and measured envelope are documented. Any new source or visibly different sample must be checked again; procurement or fabrication needs separate approval.
