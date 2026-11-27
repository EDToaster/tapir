# Tapir Rev A | electrical handoff

Open `left/tapir-left.kicad_pro` and `right/tapir-right.kicad_pro` separately in **KiCad 10.0.8**. These are physically distinct two-layer carriers, not the same PCB flipped over. The native schematics, boards, editable libraries, component STEP files and local tables live together here. Nothing in this directory is a purchase, fabrication or assembly authorization.

## What is on the carrier

| Circuit | Left | Right | Electrical contract |
|---|---:|---:|---|
| SW1–21 + D1–21 | 21 | 21 | Direct-solder Kailh CPG135001D01. P1 = column, P2 = corresponding diode anode; diode pad 1/cathode returns to ROW. One diode per physical switch. |
| SW22–24 + D22–24 | 3 | 0 | PTS810SJM250SMTR LFS. R3C0 = left click; R3C1 = scroll hold; R3C2 = right click. Thumb keys remain R3C3/4/5, outer to inner. |
| U1 | 1 | 1 | [Seeed XIAO nRF52840 Plus, non-Sense](https://www.seeedstudio.com/Seeed-Studio-XIAO-nRF52840-Plus-p-6359.html), 102010672. Surface-mount the module, including its underside pads. Header-mounted or non-Plus boards do not implement this carrier. |
| J1, S1 | 1 each | 1 each | [Protected 100 mAh pack](https://www.adafruit.com/product/1570); factory PH termination, no cutting or battery soldering. J1.1 = CELL_PLUS, J1.2 = GND. S1.2 = cell, S1.1 = VBAT_SW, S1.3 = isolated. |
| U2, C1, C2, R1–R3, J2 | 0 | 1 each | [Active-high TPS22918DBVR](https://www.ti.com/product/TPS22918) switches the pointer's 3.3 V rail. The Sprintek driver and head are an **off-board harness assembly**, not fake components placed on the main PCB. |

Every switch row uses the same scan polarity. Local columns run outer to inner on both hands; firmware reverses the right physical column order when forming the Corne logical layout. The matrix path is COL → switch → diode A → diode K → ROW. The left mouse controls are physical, diode-isolated inputs, not overloaded key combinations.

### Module interface

| Carrier U1 pads | Module pins | Use |
|---|---|---|
| 1, 2, 3, 4 | D0…D3 | ROW0…ROW3 |
| 5, 6, 7, 8, 9, 10 | D4…D9 | COL0…COL5 |
| 11, 15, 16, 17 | D10/P1.15, D11/P0.15, D12/P0.19, D13/P1.01 | Right: PS2_DATA, PS2_CLK, PS2_RST, PTR_EN. Left: intentionally unused. |
| 12, 13, 14 | 3V3, ground, VBUS | U1.12 supplies only the right pointer circuit. No carrier VBUS load; USB data, ESD, connector and charger are on U1. |
| 18–23 | D14…D19 | All intentionally unused. D14/15 are shared with NFC; D16 is a battery-sense pin. |
| 24, 25, 26, 27 | SWDIO, SWDCLK, nRESET, ground | First three are unused host pads; 27 is connected to carrier GND. Use the module button for recovery, removing the right bridge with the cell disconnected. No side-access SWD header is claimed. |
| 28, 29 | BAT+, BAT− | VBAT_SW and GND. These are invisible once the XIAO is installed: confirm land overlap, paste transfer and solder quality on a coupon/sample before accepting assembly. |

Numbering is the **host footprint**, not the GPIO number. The [Seeed Plus board artwork](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip), [host land pattern](https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip) and [Zephyr Plus pin table](https://docs.zephyrproject.org/latest/boards/seeed/xiao_nrf52840_plus/doc/index.html) are the basis. The host battery lands are not exactly centered on the module's actual rectangles: see `reports/xiao-hidden-lands.json` for the explicit geometry comparison. That is a land-overlap audit, not inspection of a solder joint.

### Power and pointing assembly

S1 disconnects **the cell**, not USB. Switch open + cable attached means the MCU can still run and the cell cannot charge. With S1 closed the module's onboard charger is connected to the cell. Do not fit an additional charger or assume that the mere presence of pack protection makes an unknown charge setting safe. [Seeed specifies high-impedance P0.13 without pulls for approximately 50 mA](https://wiki.seeedstudio.com/XIAO_BLE/); check every bootloader/application startup path and measure cell current before unattended use. The [1570 pack drawing and electrical limits](https://cdn-shop.adafruit.com/product-files/1570/1570datasheet.pdf) take precedence over marketing dimensions.

**Check polarity before mating the real cell.** In the [Adafruit Feather M0 rev C PCB](https://github.com/adafruit/Adafruit-Feather-M0-Basic-Proto-PCB/blob/master/Adafruit%20Feather%20M0%20Basic%20rev%20C.brd), X1 pad 2 is VBAT and pad 1 is ground. Its Eagle XY and mating orientation differ from the [KiCad JST footprint](https://gitlab.com/kicad/libraries/kicad-footprints/-/blob/10.0.8/Connector_JST.pretty/JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod): align the **physical mating faces**, not printed pad numbers. In Tapir the left native pad (−1,−2.85) is +, the right pad (+1,−2.85) is −. Confirm the actual pack with a meter at its unplugged housing, then continuity from an unpowered mated dummy pigtail through J1/S1 to U1 pads 28/29. Do not probe by shorting adjacent live contacts. Do not connect anything if these checks disagree.

Right J2 is a row of five wire terminations, not an 8-pin FFC footprint. Read the actual **Method 1 castellated** pin-1 mark on the [Sprintek SK8707-01-004 drawing, pages 3–4](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=3). Do not use the pin numbering of either FFC alternative.

| J2 → Sprintek Method 1 | Signal | Expected |
|---|---|---|
| 1 → 1 | GND | Common return; square pad marks carrier pin 1. |
| 2 → 2 | PS2_DATA | Open drain; 4.7 kΩ to PTR_3V3, never to unswitched 3V3. |
| 3 → 3 | PS2_CLK | Same pull-up scheme; no pull-ups enabled from the MCU when off. |
| 4 → 4 | PS2_RST | Active high. Hold low or release as appropriate; never drive high with driver VCC off. |
| 5 → 5 | PTR_3V3 | U2.6. U2.5 QOD is tied here to discharge the rail. U2.4 CT is deliberately open; R3 100 kΩ defaults EN low. |
| None → 6,7,8 | Driver mouse inputs | Not wired to the carrier or left half. |

Keep the four raw sensor-to-driver connections separate from this five-wire host cable. Fit the original matched driver/head pair from the **3.3 V detached –004** kit; maintain sensor/driver matching marks and verified wiring order. If the kit is not already terminated, label both sides of each of the four wires from the supplied sensor/driver markings or vendor guidance; do not infer pin order from a generic donor or trace color. Do not power until checked. Keep sensor wires short and strain relieved, away from switch tails, the antenna and moving parts. Insulate driver solder joints from the carrier; the separate bridge must take pointing loads. Physical retention, reach, lead dress, calibration and assembled RSSI are prototype gates.

R1/R2 draw about 0.70 mA per line, but only while that line is low and the rail is enabled. The right driver itself draws a typical [2.09 mA active, 0.65 or 1.44 mA idle depending on Z-tap, and 40 µA in its power-down mode](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=5). U2's 1 µF input / 0.1 µF local output is a 10:1 local ratio; the module's unknown internal capacitance and cable add to the load. Scope turn-on droop, discharge, clock edges and leakage with the real assembly; do not convert these nominal figures into a measured keyboard runtime.

## Stackup, drawings and gates

Target standard **2-layer FR-4, finished 1.6 mm, 1 oz outer copper, ENIG, tented vias**; no impedance-controlled bus is routed on the carrier. Nominal signal traces are 0.20 mm, power/ground 0.30 mm, copper spacing at least 0.20 mm, copper to routed edge 0.30 mm, copper to unrelated drilled holes 0.25 mm. Through vias are 0.60/0.30 mm (signal) or 0.65/0.30 mm (power); carrier-mount NPTHs are Ø2.20 mm with Ø5.40 keepouts. These are design targets, not a board-house quote; recheck the [JLCPCB rigid production capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/) and actual stack/finish/tolerance at release. Solder/paste process, panel rails, tool access, registration, coupon and drill compensation need fabrication review.

Do not mirror any offset a second time. In the PCB editor each hand uses `XY = geometry.XY + (100,100) mm`, and clockwise geometry angles become negative KiCad angles. The vendor XIAO's native USB points +X, so its exception is `rotation = 90° − geometry.a`. `step/tapir-<hand>-populated.step` uses a **100×100 mm user origin**; thus STEP XY = (geometry.x, −geometry.y) and the component seating plane is at STEP z = +1.595 mm. The exported dielectric solid is not the whole finished copper/mask stack. No detached module, bridge, battery, harness or case is pretended to exist on the native carrier STEP. See `models/` for real part versus independent fit-proxy status.

- **Electrical evidence:** `reports/tapir-<hand>-erc.json`, `...-drc.json`, `...-schematic-parity.json`, `...-routing.json`. Check report counts, `passes`, and that the board revision matches the report. Missing reports do not pass. The native DRC JSON records default advisory checks ignored by KiCad; no per-instance violations have been accepted as exclusions. Formal EDA checks cannot detect incorrect vendor pin interpretation, poor soldering, back-power, wrong firmware behavior or RF detuning.
- **Manufacturing review:** `build/fabrication/<hand>/` contains review-only Gerber X2 copper/mask/paste/silk/edge layers, separate NPTH/PTH Excellon files, drill report, machine placement/board BOM CSVs, native human-readable ERC/DRC and SHA-256 manifest. Inspect layer registration, drill classification and pin 1 by eye in an independent viewer before seeking purchase approval. Do not upload straight to checkout.
- **Library provenance:** local stock patterns are adapted from KiCad 10.0.8 (model paths localized; PCM12 actuator silk moved to assembly so it is not clipped by the edge). Stock patterns retain [KiCad's CC BY-SA 4.0 + design exception](https://www.kicad.org/libraries/license/index.html); license text is under `models/licenses/`. Seeed supplies the non-Sense Plus land pattern [in its hardware library](https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip), adapted here by removing unrelated alternate model bindings and moving outline ink to Fab. No blanket KiCad license is asserted over Seeed CAD. The original physical switch pattern references [Kailh's selected part specification](https://cdn-shop.adafruit.com/product-files/5113/CHOC+keyswitch_Kailh-CPG135001D01_C400229.pdf) and [Ergogen's solder-in Choc contact arrangement](https://github.com/ergogen/ergogen/blob/develop/src/footprints/choc.js). J2 and M2 fixtures are project-specific. Check each local model's separate credits.

## Rebuild and use

For routine KiCad edits open the native sources; generators are optional. When regenerating from a changed design, work in a disposable checkout and preserve the routed source until a candidate passes all checks:

```sh
cd product/electronics
python3 tools/design.py                       # hand circuit manifests in build/
/usr/bin/python3 tools/place_board.py          # unrouted boards in build/<hand>
python3 tools/schematic.py                     # see tools/schematic.md
# Native schematic and routing workflows:
# tools/schematic.md and tools/route.md (includes pinned local router JARs).
/usr/bin/python3 tools/route_finish.py left right  # replay bundled SES, test before and after ground fill
/usr/bin/python3 tools/route_verify.py left right
python3 -m venv /tmp/tapir-cam && /tmp/tapir-cam/bin/pip install gerbonara==1.6.3
export TAPIR_CAM_PYTHON=/tmp/tapir-cam/bin/python
python3 tools/export_handoff.py left
python3 tools/export_handoff.py right
```

For a deliberate library refresh run `python3 tools/footprints.py /path/to/New_XIAO_Series_Footprints.zip`; the vendor ZIP hash is pinned. Board object UUIDs or timestamps can change on regeneration: manufacturing comparison must examine geometry, nets, layers, rules and fresh native reports, not timestamps. Never overwrite a hand-routed ECO merely to refresh documentation.

The shipped routes replay without a JAR, JVM or network once prerequisites are installed. Each hand has fixed tracks (including a GND path), GND zones on both copper layers, and an antenna exclusion for those zones. The export verifies the board hash, reruns native all-severity ERC/DRC/parity, and independently reopens its own RS-274X/X2 and Excellon output with Gerbonara. Read `build/fabrication/<hand>/cam-readback.json`: every numbered copper land on each layer, complete drill register and profile centerline must agree. Gerbonara may note KiCad's placement of G90 after the header; it still decodes the absolute coordinates, which are compared against native pads and vias. The KiCad Gerber Job file does not encode a selected surface finish; ENIG is a **manual** order/checklist requirement, not an implied order option.
