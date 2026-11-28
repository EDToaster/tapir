# TMR half design decisions

Status values: **Decided** means the owner chose it and other work should build on it. **Proposed** is the current working assumption and can change without a formal reversal. **Open** still needs a measurement or a choice.

Evidence tags follow the repo convention. **Drawing** values come from a manufacturer document or the referenced design file. **Measured** values say who measured what. **Allowance** values are assumptions that still need checking.

Last updated 2026-11-27.

## Decision log

| # | Decision | Status | Rationale and alternatives |
| --- | --- | --- | --- |
| D1 | 6 columns × 5 rows, 28 keys; bottom row is blank, Menu, Mod1, Mod2, Alt, blank | Decided | Half-size board leaves room for a mouse. See the [layout](README.md#layout). |
| D2 | Wired USB first; Bluetooth is a bonus, not a requirement | Decided | Always-powered analog sensors make long battery life hard (see D9). The board should still keep the battery path possible. |
| D3 | Controller: nice!nano v2 clone (nRF52840), same pinout as the original | Decided | The owner already has one. Pin budget in D7. |
| D4 | Switch: Gateron Low Profile Magnetic Jade Pro (Jade is the alternate) | Decided | It has an MX-style cross stem and a low profile. It is the switch Partial-Gauss built around, so D5's placement and field measurement apply directly. It needs low-profile MX-stem caps (for example NuPhy nSA), not standard MX caps. |
| D5 | Follow Partial-Gauss sensor placement: centre the sensor 4.40 mm south of the switch centre on the PCB underside | Decided | The offset comes from the [Partial-Gauss footprint, commit 22332cc](https://github.com/cr3eperall/partialgauss/tree/22332cc41146e4ef1578647862eb83c12e0bae82) (**drawing**). Partial-Gauss reports about 400 G at its Hall sensor with a 1.6 mm PCB. [Gateron KS-33D, p. 7](https://www.gateron.com/u_file/2603/10/file/GATERONLowProfileMagneticJadeProSwitch-KS-33DD10B060NW-D276.pdf) shows a 1.20 mm PCB and specifies 75 ± 10 Gs at rest and 680 ± 70 Gs at bottom-out (**drawing**). Thickness is separate: see D12 and T1. |
| D6 | Sensor: MDT TMR2617S-AAC, factory-calibrated stock build TMR2617S-AAC-0.500-500 | Decided | Z-axis linear TMR in SOT-23-3 with the same pinout as the Partial-Gauss Hall sensor. It is calibrated at the factory, so no programming order is needed. Variant choice and stock risk in [Sensor](#sensor). |
| D7 | Readout: two TI CD74HC4067SM96 16:1 analog multiplexers (SSOP-24) with shared select lines, one ADC input each | Proposed | The nice!nano only has three free analog inputs, so 28 keys need muxes; 32 channels leave 4 spare. The ADC draws almost no current, so the mux's 70–200 Ω switch resistance only affects settling, which works out well under 1 µs. Sensor recovery is the unknown and D10 measures it. Parallel 8:1 muxes need 4 ADC pins, and an external ADC adds parts and needs a driver. Full reasoning in [analog-readout.md](analog-readout.md); pin plan in [Readout](#readout). |
| D8 | Firmware in two stages. The test board runs ZMK with [zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect) (MIT). Then custom Rust firmware (embassy-nrf, embassy-usb) with a WebUSB web page for changing thresholds. The final build runs the Rust firmware. | Decided | ZMK's `he,kscan-multiplexer` driver already handles shared select lines across several muxes, so it gets the test board scanning without new code. Its thresholds live in devicetree and need a reflash, which is what the Rust stage fixes. embassy-usb has a [WebUSB class](https://docs.rs/embassy-usb/latest/embassy_usb/class/web_usb/index.html). [RMK](https://github.com/rmk-rs/rmk/discussions/525) has no analog matrix yet. See [Firmware](#firmware). |
| D9 | Put a switch on the sensor power rail. Firmware decides whether to pulse it. | Proposed | 28 sensors draw up to 8.4 mA whenever powered, which only matters on battery. The switch is cheap and keeps D2's battery option open. Pulsing saves little at 1 kHz because the 100 nF bypass capacitors refill on every pulse. Budget in [Power](#power). |
| D10 | Build a 2 × 3 key test coupon before the full board. Design is in [coupon/](coupon/README.md); not ordered. | Proposed | Confirms the field at the TMR2617S and the 0.5 vs 0.75 choice. Also measures mux settling, noise and pulsed-power behaviour, with 100 nF and 10 nF bypass capacitors, and with and without the optional 0.1 nF output capacitor. The owner asked for the coupon and delegated its design choices, listed in [Test coupon](#test-coupon). |
| D11 | Build a small bare-metal coupon test program as the first slice of the Rust firmware in D8 | Proposed | T3 needs a controlled delay from address change to sampling. T6 needs control of the rail pins and a timed read of a key. Keep ZMK for bring-up and the steady-state tests. No test firmware is implemented yet. |
| D12 | Compare nominal 1.2 mm and 1.6 mm coupons before choosing full-board thickness | Proposed | T1 will compare measured thickness, field and travel swing using the same design and parts. The owner chooses assembled batches or one assembled thickness plus bare boards to hand-populate. |
| D13 | Put an AO3401A series reverse-polarity FET and a reverse-polarity indicator ahead of the battery switch | Proposed | Q3 blocks the usual battery-only reverse connection. The LED checks the raw battery polarity with the switch off. With USB connected and the switch on, the charger can turn Q3 on even with a reversed pack. Follow the [battery first-connection procedure](coupon/README.md#optional-battery). |
| D14 | Use unrestricted P0 pins for sensor-rail control on the 28-key board | Proposed | Coupon rail B uses P1.04, which the [Nordic pin table](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/pin.html) lists as standard drive, low-frequency I/O only (**drawing**). Verify the exact full-board pins against Nordic's restrictions and the actual module. |
| D15 | Use C&K PCM12SMTR on the coupon and leave charge boost open | Proposed | The [C&K drawing](https://www.littelfuse.com/assetdocs/littelfuse-ck-slide-pcm-series-datasheet?assetguid=d2f6a96c-7a9a-4c4e-a5aa-4fe3075dffe5) rates it for 300 mA at 6 V DC. Standard module charging is about 100 mA; boost can use the entire rating or exceed it. Verify the actual module. |
| D16 | Interleave grounded mux addresses between live keys, with MON on 7 | Proposed | Live keys use 1/3/5 on each mux. Addresses 0/2/4/6 and 8–15 are grounded. This gives T3 adjacent grounded channels and allows a route with no measured close same-layer analog/control parallel runs. |
| D17 | Use the checked-in two-layer route for review; keep its coverage gaps visible | Proposed | The [layout report](coupon/reports/analog-layout.json) shows three of ten analog nets at or above 80% opposite-layer ground and at least two through stitches per filled region. Per-net lower limits guard against regression. Owner approval and T2–T4 are still needed. |
| D18 | Accept the rev A warning LED's continuous reverse bias for the bench coupon without a series protection diode | Proposed | At a 4.2 V pack maximum, D1 is 0.8 V below its 5 V absolute reverse maximum. The [KT-0603R datasheet](https://www.lcsc.com/datasheet/lcsc_datasheet_1810231112_Hubei-KENTO-Elec-KT-0603R_C2286.pdf) specifies ≤5 µA at 5 V and 25 °C, not life or actual off-state drain. Use the current-limited indicator check and verify pack polarity with a meter. Revisit added protection for a full board. |
| D19 | Add S0–S3 pull-downs on the full board, starting at 100 kΩ each | Proposed | Rev A leaves the lines without pulls; an undriven address has undefined selection and can raise mux input supply current. Check leakage, credible logic margins and sleep current on the full board before choosing the final values. |

## Sensor placement

Source: Partial-Gauss footprint `gauss_lib.pretty/HE_KB_switch.kicad_mod` at commit [22332cc](https://github.com/cr3eperall/partialgauss/tree/22332cc41146e4ef1578647862eb83c12e0bae82). Coordinates are KiCad footprint coordinates in mm from the switch center, with +Y toward the bottom of the board (south). All values are **drawing** values from that file.

| Feature | Position (x, y) | Size | Notes |
| --- | --- | --- | --- |
| Center hole (NPTH) | (0, 0) | Ø5.1 | Switch housing post |
| Side holes (NPTH) | (±5.08, 0) | Ø1.7 | Switch alignment posts. The switch has no electrical pins, so the plate or case must hold it. |
| Sensor pad 1 (VIN) | (+0.95, 3.35) on F.Cu; (−0.95, 3.35) on B.Cu | 1.1 × 0.6 | Partial-Gauss is reversible, so the pads are mirrored per side |
| Sensor pad 2 (OUT) | (−0.95, 3.35) on F.Cu; (+0.95, 3.35) on B.Cu | 1.1 × 0.6 | |
| Sensor pad 3 (GND) | (0, 5.45) | 1.1 × 0.6 | |
| Sensor body center | (0, 4.40) | SOT-23-3 | Midpoint between the pad rows |
| Bypass capacitor (0805) | (+2.93, 3.6) and (+2.93, 5.65) on F.Cu; mirrored to x = −2.93 on B.Cu | 1.15 × 1.4 | Between VIN and GND |

Choices for this project:

- Use a single-sided sensor placement. Put the sensor on B.Cu under the switch at the 4.40 mm offset shown above (**drawing**). Partial-Gauss reports about 400 G through its [1.6 mm PCB](https://github.com/cr3eperall/partialgauss/blob/22332cc41146e4ef1578647862eb83c12e0bae82/gauss.kicad_pcb) (**measured** by Partial-Gauss with its DRV5053 layout; measurement method and rest value unstated, see its [Notes](https://github.com/cr3eperall/partialgauss/blob/22332cc41146e4ef1578647862eb83c12e0bae82/README.md#notes)).
- The [Gateron KS-33D drawing, p. 7](https://www.gateron.com/u_file/2603/10/file/GATERONLowProfileMagneticJadeProSwitch-KS-33DD10B060NW-D276.pdf) shows its Hall sensor under a 1.20 mm PCB. The adjacent mechanical view specifies 1.20 ± 0.05 mm. The drawing shows the magnet's north pole facing down and specifies 75 ± 10 Gs at rest and 680 ± 70 Gs bottomed (**drawing**). Nominal travel swing is 680 − 75 = 605 Gs, or about 1.00 V at 3.3 V with the selected TMR sensitivity if it sees the same field. The Partial-Gauss ~400 G reading would give a nominal 0.66 V change from zero field; its actual travel swing is unknown. The readings come from different sensor stacks, so the ratio of the two reported endpoint fields does not predict the resolution gain. Measure both thicknesses in T1.
- At the high end of Gateron's tolerance, 680 + 70 = 750 Gs. That is 250 Gs below the TMR2617S-AAC family linear limit of 1,000 Gs ([MDT datasheet, pp. 2, 4–5](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf), **drawing**). The 0.500-500 variant also has an output swing limit: (0.95 − 0.50) / 0.000500 = 900 Gs nominal. At 750 Gs, the output moves 0.375 × VCC from midscale, to 12.5% or 87.5% of VCC depending on polarity. That leaves 7.5% of VCC, or 150 Gs nominal, before the nearer output limit. The 0.75 variant would nominally clip above 600 Gs at the same offset. These estimates use nominal calibration. Verify on the coupon because sensing height, offset and magnet strength can vary.
- Keep a 100 nF bypass capacitor at every sensor. The [TMR2617S-AAC datasheet](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf) specifies C1 = 0.1 µF "as close as possible to the VCC and GND pins". Partial-Gauss reports more noise without them. The cost is a slower rail rise when power is pulsed, which D10 measures.
- Pinout matches without remapping. The Partial-Gauss schematic symbol maps pad 1 VIN, 2 OUT, 3 GND. The TMR2617S-AAC datasheet gives 1 VCC, 2 VOUT, 3 GND (**drawing**, both).
- Redraw the footprint in this project rather than copying the file. Partial-Gauss has no LICENSE file at the commit above. The dimensions here are recorded so the footprint can be rebuilt independently, with attribution.

## Sensor

MDT [TMR2617S-AAC](https://www.dowaytech.com/en/TMR2617S-AAC-TMR-Linear-Sensors.html) facts used here, all **drawing** from the [datasheet](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf):

- SOT-23-3, Z-axis (perpendicular to the board) sensing, linear range ±1000 Gs.
- 1.71–5 V supply, static current under 300 µA, power-on time 100 µs max.
- Output 5–95% of VCC and ratiometric to VCC. Load capacitance 10 nF max.
- Part number TMR2617S-AAC-[sensitivity]-[offset]. Sensitivity is 0.100–2.000 mV/V/Gs; offset is in mV/V, so 500 means 50% of VCC at zero field. The "A" code means sensitivity and offset are calibrated at the factory.

The output saturates at 45% of VCC either side of the 50% offset, so the usable field is 450 / sensitivity in Gs:

| Build | Signal at 3.3 V | Saturates at | Swing at 400 G | Orderable listing |
| --- | --- | --- | --- | --- |
| 0.500-500 (selected) | 1.65 mV/Gs | ~900 G | 20% VCC, 0.66 V, ~820 counts at 12 bits | [LCSC C55130211](https://www.lcsc.com/product-detail/C55130211.html), [JLCPCB C55130211](https://jlcpcb.com/partdetail/58850683-TMR2617S_AAC_0_500500/C55130211), [JLCPCB Assembly C9900288929](https://jlcpcb.com/partdetail/58837036-TMR2617S_AAC_0_500500/C9900288929) |
| 0.75 (alternate) | ~2.5 mV/Gs | ~600 G | 30% VCC, ~0.99 V | [JLCPCB Assembly C9900176377](https://jlcpcb.com/partdetail/JLCPCBAssembly-TMR2617S_AAC_075/C9900176377); the listing does not state sensitivity or offset |
| Custom | Any 0.100–2.000 | — | — | Programmed to order through [Calero](https://tmr-sensors.com/products/tmr2617) |

The counts column is a **nominal calculation** assuming a 12-bit SAADC with a VDD/4 reference at gain 1/4, so full scale equals VDD.

Why 0.500-500:

- It is the only build with an exact, published part-number suffix and a catalog listing.
- It leaves more than 2× headroom over the ~400 G Partial-Gauss reading. That covers a TMR sensing element that may sit at a different depth or offset than the DRV5053's.
- Its signal per gauss is about the same as typical Hall sensors ([GRIDDLE LX](https://erfi.dev/reference/griddle-lx-hall-effect-keyboard/)). The gain over Hall is the roughly 20× lower current, not resolution.

Gateron gives the field and its reference geometry in the KS-33D drawing. The 0.500-500 headroom calculation is in [Sensor placement](#sensor-placement). Keep the 0.75 option open until T1 shows the worst-case endpoints and the smallest travel swing. A nominal endpoint close to 600 Gs leaves little margin on a 0.75 build with the same offset.

Stock flag: on 2026-11-27, C55130211 showed zero stock at both JLCPCB and LCSC. See [Sensor stock](coupon/README.md#sensor-stock) for the dated minimum buy, pricing and alternatives.

## Readout

Free analog inputs on the nice!nano v2 are P0.02 (AIN0), P0.29 (AIN5) and P0.31 (AIN7). P0.04 (AIN2) is wired to battery sensing.

| Signal | Pin | Notes |
| --- | --- | --- |
| Mux A output | P0.02 / AIN0 | Keys 1–16 |
| Mux B output | P0.29 / AIN5 | Keys 17–28, 4 spare channels |
| S0–S3 select lines | 4 digital GPIOs, shared by both muxes | Both muxes present their selected channels together. The nRF52840 SAADC samples the two pins in sequence. |
| Mux enable (active low) | Tie low, or 1 shared GPIO | |
| Mux B spare channels | 4 | Reserve a rail-monitor channel and distribute grounded inputs where the pin and routing budget allow. See [Supply and reference](analog-readout.md#supply-and-reference). |
| Sensor power enable | 1 GPIO driving the D9 load switch or P-MOSFET | Not P0.13, which controls the controller's own VCC output |
| Spare analog | P0.31 / AIN7 | Free for a debug channel or a future battery divider |

These pins are an **allowance**: check them against the clone's actual board before routing. Don't tie TMR2617S outputs together without a mux. Keep the muxes powered from the 3.3 V supply during sensor pulsing. Before turning off either sensor rail or the module's 3.3 V supply, stop sampling and drive the address lines low. See [Circuit rules](analog-readout.md#circuit-rules-for-the-schematic).

## Power

Each TMR2617S draws up to 300 µA whenever it has power, whether or not it is being read. 28 of them draw up to 8.4 mA. USB supplies hundreds of milliamps, so this only matters on battery.

Pulsing means switching the sensors on before a scan and off afterwards. For an illustrative budget, use 100 µs sensor power-on time from the MDT datasheet (**drawing**) plus the 192 µs hardware-only scan estimate. That gives a 292 µs on-time estimate before rail rise time, firmware and averaging. In the fully discharged case, each 100 nF bypass capacitor takes 100 nF × 3.3 V = 0.33 µC to refill. Each sensor draws up to 300 µA × 292 µs = 0.0876 µC while powered. For 10 nF, the refill term is 0.033 µC.

The following **estimates** use 28 sensors and full capacitor discharge between scans. Each pulsed figure is frequency × 28 × (refill charge + sensor charge). Controller, divider and switch consumption are excluded. T6 measures actual wake time and rail behavior.

| Mode | 100 nF bypass | 10 nF bypass |
| --- | --- | --- |
| Always on | Up to 8.4 mA | Up to 8.4 mA |
| Pulsed, 1 kHz | 11.7 mA | 3.38 mA |
| Pulsed, 100 Hz | 1.17 mA | 0.338 mA |
| Pulsed, 20 Hz idle | 0.234 mA | 0.068 mA |

Switching can cost more current than leaving the sensors on if the bypass capacitors discharge far enough. Real rails may retain charge. Compare measured current and noise before changing the bypass or pulsing policy.

The switch also sees 28 × 100 nF = 2.8 µF of capacitance at every turn-on. Pick a load switch with controlled turn-on, or a P-MOSFET sized for that current spike (Partial-Gauss used IRLML2402 MOSFETs). The rise time adds to the on-time above.

Plan:

- Hardware: include the switch. It costs one small part and one GPIO.
- ZMK test board: sensors always on. The `he,kscan-multiplexer` driver has no sensor-enable pin; only `he,kscan-direct-pulsed` pulses. Also check for nRF52840 [anomaly 212](https://docs.nordicsemi.com/bundle/errata_nRF52840_Rev2/page/ERR/nRF52840/Rev2/latest/err_840.html) if both drivers are ever enabled.
- Rust firmware: always on while scanning at 1 kHz over USB. Optionally drop to a slow pulsed scan after a period of no key activity, for future battery use.
- D10 coupon: compare the fitted 100 nF and 10 nF options first. Measure rail rise and key settling in T6. A no-bypass comparison requires removing parts deliberately. Only reduce bypass if T2 shows acceptable noise; MDT specifies 0.1 µF in its application circuit (**drawing**).

## Test coupon

The owner asked for a 2 × 2 or 2 × 3 coupon with an optional battery connection and on-off switch, and left the remaining choices to the designer. These are **Proposed** until the owner confirms them. Details, files and the test plan are in [coupon/README.md](coupon/README.md).

| Choice | Value | Why |
| --- | --- | --- |
| Size | 2 × 3 keys at 19.05 mm, 92 × 50 mm, 2 layers (**drawing**) | T1 compares nominal 1.2 mm and 1.6 mm. Three keys per rail let the centre key be tested with two same-rail neighbours. |
| Mux | Two CD74HC4067SM96, shared select lines, one ADC pin each | Same architecture as D7. The coupon puts grounded inputs between live channels. The full board will have more populated channels, so recheck settling on it. |
| Sensor rails | Two, each with an AO3401A, 10 Ω shunt and 10 kΩ / 10 kΩ monitor divider | Keys use addresses 1, 3 and 5 on each rail; MON is address 7. All others read ground. |
| Bypass | 100 nF on rail A (K1–K3), 10 nF on rail B (K4–K6) | Datasheet value against a faster-rising rail |
| Output capacitor | 100 pF on K2 and K5 only | Compare against bare neighbours |
| Battery | JST S2B-PH-SM4-TB(LF)(SN), AO3401A Q3, S1 and a reverse-polarity LED on the raw battery side | Uses the module's own charger through C&K PCM12SMTR. D1 and R15 are the warning indicator and its 1 kΩ series resistor. |
| Assembly | Bottom-side SMT; controller and switches fitted by hand | 42 fitted SMT placements. |
| Routing | Analog-to-control spacing and ground-return checks | See [coupon layout measurements](coupon/README.md#layout). Recheck noise and crosstalk on both thicknesses. |
| Decorative silkscreen | Quadtree Truchet (pattern 03 in [silkscreen-patterns](../silkscreen-patterns/)) on both sides at 2× zoom, cut back 0.30 mm from pads, holes, courtyards and other marks | The owner asked for this pattern, zoomed in, on top and bottom. The zoom, the two crop windows and the clearances are the designer's picks. Cosmetic only; copper is unchanged. |

Pins on the coupon: S0–S3 on P0.17, P0.20, P0.22, P0.24; mux enable on P1.00; rail switches on P0.11 and P1.04; ADC on P0.02 and P0.29; P0.31 spare. Pin positions come from the [nice!nano v2 pinout](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/) (**drawing**); the clone has not been checked against it.

P1.04 is marked standard drive, low-frequency I/O only ([Nordic pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/pin.html), **drawing**). Keep coupon rail B switching slow. D14 proposes unrestricted P0 pins for the 28-key board.

Verification so far is design-level only: KiCad ERC and DRC with schematic parity report no violations, and the Gerber and drill files were read back and compared with the board. Nothing is **measured**.

## Polling and rapid trigger

- USB on the nRF52840 is full-speed only, so the report rate tops out at 1 kHz ([Nordic USBD](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/usbd.html)). BLE connection intervals are 7.5 ms or longer.
- A full scan uses 16 shared mux addresses and two sequential SAADC conversions per address. The hardware-only time budget is about 192 µs at a 2 µs settle and 480 µs at a 20 µs settle, assuming 3 µs acquisition and roughly 2 µs conversion per sample. These are estimated lower bounds for complete scans. Driver overhead, longer acquisition, averaging and processing add time. See [Analog readout](analog-readout.md#why-the-cheap-74hc4067-is-enough).
- ZMK requests a kernel sleep for the mux delay. Measure the achieved sample and report rates on hardware. Use the bare-metal build for the controlled T3 timing sweep.

## Firmware

Stage 1, coupon bring-up: use ZMK with zmk-feature-hall-effect. Its raw calibration log can support T1, T2, T4 and T7 while the sensor rails stay on. T5 and T8 also use a meter. See the [coupon test plan](coupon/README.md#test-plan).

Stage 2, Rust firmware (embassy-nrf and embassy-usb): the proposed first slice is a small bare-metal coupon build for T3 and T6. It will use a short busy-wait or a hardware timer, switch the sensor rails and buffer samples before logging. The final board will run the Rust keyboard firmware described below.

- USB HID keyboard at 1 kHz plus a vendor WebUSB interface. embassy-usb ships a `web_usb` class behind its `class-web-usb` feature ([docs.rs](https://docs.rs/embassy-usb/latest/embassy_usb/class/web_usb/index.html)).
- A static web page talks to the board over WebUSB to read live key travel and set per-key actuation point, release point and rapid-trigger sensitivity. WebUSB works in Chromium-based browsers (Chrome, Edge) and not in Firefox or Safari.
- Settings persist in internal flash, so they survive unplugging.
- Per-key rest and bottom-out calibration, since magnets and sensor offsets vary.
- Busy-wait settle timing, so the mux delay is exact.

## Open questions

- Package fit: confirm the TMR2617S-AAC SOT-23-3 outline against the Partial-Gauss land pattern. The datasheet shows a "Sensor Area" but the extracted text gave no dimensions.
- Field and thickness: measure actual board thickness and compare rest, travel and bottomed readings in T1. This informs the final thickness and the 0.500 vs 0.75 choice.
- Mux settling: use T3 to alternate two live keys at different levels and then a key and ground on each mux. Sweep a busy-wait delay. Repeat with and without the 100 pF output capacitor.
- Clone power rail: check the actual module's B+, VCC voltage and P0.13 behavior. The [genuine nice!nano v2 ZMK overlay](https://github.com/zmkfirmware/zmk/blob/main/app/boards/nicekeyboards/nice_nano/nice_nano_nrf52840_zmk_2_0_0.overlay) enables external power with a high on P0.13 (**drawing**). Use T7 to compare raw and rail-normalized readings across power sources.
- Pulsed-power settling: T6 reads a key at stepped delays after power-on. Use the rail monitor or a scope to check rail voltage separately. Leave both rails on for the initial ZMK tests.
- Sensor power switch part: the coupon uses an AO3401A P-MOSFET. Keep it or move to a load switch IC after the coupon shows the inrush and rise time.
- Mux footprint: SSOP-24 (CD74HC4067SM96) is the plan and is on the coupon; TSSOP-24 and SOIC-24 second sources need different footprints.
- Coupon ordering: sensor stock, placement rotations and battery plug polarity need checking at order and bring-up time ([coupon/README.md](coupon/README.md)).
- Retention: the switch has no electrical pins. Choose a plate or case approach (Partial-Gauss uses a 3D-printed plate).
- Keycaps and case: low-profile MX-stem caps; enclosure TBD.
