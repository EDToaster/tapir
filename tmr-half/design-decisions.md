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
| D5 | Follow Partial-Gauss sensor placement: sensor centered 4.40 mm south of the switch center on the bottom side of a 1.6 mm PCB | Decided | This is the only placement found with a published field measurement for this switch. Geometry in [Sensor placement](#sensor-placement). |
| D6 | Sensor: MDT TMR2617S-AAC, factory-calibrated stock build TMR2617S-AAC-0.500-500 | Decided | Z-axis linear TMR in SOT-23-3 with the same pinout as the Partial-Gauss Hall sensor. It is calibrated at the factory, so no programming order is needed. Variant choice and stock risk in [Sensor](#sensor). |
| D7 | Readout: two TI CD74HC4067SM96 16:1 analog multiplexers (SSOP-24) with shared select lines, one ADC input each | Proposed | The nice!nano only has three free analog inputs, so 28 keys need muxes; 32 channels leave 4 spare. The ADC draws almost no current, so the mux's 70–200 Ω switch resistance only affects settling, which works out well under 1 µs. Sensor recovery is the unknown and D10 measures it. Parallel 8:1 muxes need 4 ADC pins, and an external ADC adds parts and needs a driver. Full reasoning in [analog-readout.md](analog-readout.md); pin plan in [Readout](#readout). |
| D8 | Firmware in two stages. The test board runs ZMK with [zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect) (MIT). Then custom Rust firmware (embassy-nrf, embassy-usb) with a WebUSB web page for changing thresholds. The final build runs the Rust firmware. | Decided | ZMK's `he,kscan-multiplexer` driver already handles shared select lines across several muxes, so it gets the test board scanning without new code. Its thresholds live in devicetree and need a reflash, which is what the Rust stage fixes. embassy-usb has a [WebUSB class](https://docs.rs/embassy-usb/latest/embassy_usb/class/web_usb/index.html). [RMK](https://github.com/rmk-rs/rmk/discussions/525) has no analog matrix yet. See [Firmware](#firmware). |
| D9 | Put a switch on the sensor power rail. Firmware decides whether to pulse it. | Proposed | 28 sensors draw up to 8.4 mA whenever powered, which only matters on battery. The switch is cheap and keeps D2's battery option open. Pulsing saves little at 1 kHz because the 100 nF bypass capacitors refill on every pulse. Budget in [Power](#power). |
| D10 | Build a 2–4 key test coupon before the full board | Proposed | Confirms the field at the TMR2617S and the 0.5 vs 0.75 choice. Also measures mux settling, noise and pulsed-power behaviour, with 100 nF, 10 nF and no bypass capacitor, and with and without the optional 0.1 nF output capacitor. |

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

- Single-sided rather than reversible. The sensor goes on the bottom (B.Cu), on the opposite side from the switch. Partial-Gauss reports about 400 G at the sensor with this arrangement (**measured** by Partial-Gauss with a DRV5053, method not stated; [README notes](https://github.com/cr3eperall/partialgauss#notes)).
- Keep the 1.6 mm board thickness ([gauss.kicad_pcb](https://github.com/cr3eperall/partialgauss/blob/22332cc41146e4ef1578647862eb83c12e0bae82/gauss.kicad_pcb), **drawing**). The 400 G figure depends on the magnet-to-sensor distance.
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

Stock flag: LCSC showed C55130211 out of stock on 2026-11-27 (1+ at $0.4989, 200+ at $0.2006). Recheck JLCPCB and LCSC before ordering. Switch to 0.75 if the coupon shows less than about 600 G at bottom-out.

## Readout

Free analog inputs on the nice!nano v2 are P0.02 (AIN0), P0.29 (AIN5) and P0.31 (AIN7). P0.04 (AIN2) is wired to battery sensing.

| Signal | Pin | Notes |
| --- | --- | --- |
| Mux A output | P0.02 / AIN0 | Keys 1–16 |
| Mux B output | P0.29 / AIN5 | Keys 17–28, 4 spare channels |
| S0–S3 select lines | 4 digital GPIOs, shared by both muxes | The ZMK multiplexer driver samples both muxes at the same address in parallel |
| Mux enable (active low) | Tie low, or 1 shared GPIO | |
| Mux B spare channels | 4 | 3 tied to GND as a known zero, 1 reading the sensor rail through a divider ([Supply and reference](analog-readout.md#supply-and-reference)) |
| Sensor power enable | 1 GPIO driving the D9 load switch or P-MOSFET | Not P0.13, which controls the controller's own VCC output |
| Spare analog | P0.31 / AIN7 | Free for a debug channel or a future battery divider |

These pins are an **allowance**: check them against the clone's actual board before routing. Don't tie TMR2617S outputs together without a mux. Power the muxes from the always-on 3.3 V rail, never the switched sensor rail. Schematic rules are in [analog-readout.md](analog-readout.md#circuit-rules-for-the-schematic).

## Power

Each TMR2617S draws up to 300 µA whenever it has power, whether or not it is being read. 28 of them draw up to 8.4 mA. USB supplies hundreds of milliamps, so this only matters on battery.

Pulsing means switching the sensors on just before a scan and off right after. The sensor needs up to 100 µs to wake (tPO, **drawing**) and a scan takes roughly 180 µs, so it is on for about 280 µs per scan. The catch is the 100 nF bypass capacitor at every sensor. Each pulse has to refill it before the sensor works, and that charge (C × V = 0.33 µC per sensor at 3.3 V) is more than the sensor itself uses while awake (300 µA × 280 µs = 0.084 µC). The earlier estimates here left the capacitors out.

Upper-bound sensor current, assuming the capacitors drain fully between pulses. **Nominal calculation**; how the sensor's current behaves on a decaying rail is not specified:

| Mode | 100 nF bypass | 10 nF bypass |
| --- | --- | --- |
| Always on | 8.4 mA | 8.4 mA |
| Pulsed, 1 kHz | no real saving, ~8.4 mA | ~3.3 mA |
| Pulsed, 100 Hz | ~1.2 mA | ~0.33 mA |
| Pulsed, 20 Hz idle | ~0.23 mA | ~0.07 mA |

The switch also sees 28 × 100 nF = 2.8 µF of capacitance at every turn-on. Pick a load switch with controlled turn-on, or a P-MOSFET sized for that current spike (Partial-Gauss used IRLML2402 MOSFETs). The rise time adds to the on-time above.

Plan:

- Hardware: include the switch. It costs one small part and one GPIO.
- ZMK test board: sensors always on. The `he,kscan-multiplexer` driver has no sensor-enable pin; only `he,kscan-direct-pulsed` pulses. Also check for nRF52840 [anomaly 212](https://docs.nordicsemi.com/bundle/errata_nRF52840_Rev2/page/ERR/nRF52840/Rev2/latest/err_840.html) if both drivers are ever enabled.
- Rust firmware: always on while scanning at 1 kHz over USB. Optionally drop to a slow pulsed scan after a period of no key activity, for future battery use.
- D10 coupon: measure rail rise and readings with 100 nF, 10 nF and no bypass capacitor. Only reduce the capacitor if noise stays acceptable, since the datasheet asks for 0.1 µF.

## Polling and rapid trigger

- USB on the nRF52840 is full-speed only, so the report rate tops out at 1 kHz ([Nordic USBD](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/usbd.html)). BLE connection intervals are 7.5 ms or longer.
- A full scan is 16 mux addresses × 2 parallel channels. With a 2 µs settle per address it takes about 190 µs, and about 480 µs at 20 µs settle. Both fit inside a 1 ms report ([analog-readout.md](analog-readout.md#why-the-cheap-74hc4067-is-enough)).
- ZMK's mux settle delay is a kernel sleep, so short requested delays may stretch to the tick length. Measure the real scan rate on the test board.

## Firmware

Stage 1, test board: ZMK with zmk-feature-hall-effect. Thresholds and rapid-trigger sensitivity are devicetree values, so each change is a rebuild and reflash. That is acceptable for bring-up and for the D10 measurements.

Stage 2, final build: custom Rust firmware on embassy-nrf and embassy-usb.

- USB HID keyboard at 1 kHz plus a vendor WebUSB interface. embassy-usb ships a `web_usb` class behind its `class-web-usb` feature ([docs.rs](https://docs.rs/embassy-usb/latest/embassy_usb/class/web_usb/index.html)).
- A static web page talks to the board over WebUSB to read live key travel and set per-key actuation point, release point and rapid-trigger sensitivity. WebUSB works in Chromium-based browsers (Chrome, Edge) and not in Firefox or Safari.
- Settings persist in internal flash, so they survive unplugging.
- Per-key rest and bottom-out calibration, since magnets and sensor offsets vary.
- Busy-wait settle timing, so the mux delay is exact.

## Open questions

- Package fit: confirm the TMR2617S-AAC SOT-23-3 outline against the Partial-Gauss land pattern. The datasheet shows a "Sensor Area" but the extracted text gave no dimensions.
- Field at the TMR2617S: measure it on the coupon at rest and at bottom-out. This decides 0.5 vs 0.75.
- Mux settling: hold one key bottomed and read the next channel on the same mux while sweeping the settle delay from 20 µs down to 1 µs (the [GRIDDLE LX](https://erfi.dev/reference/griddle-lx-hall-effect-keyboard/) method). Repeat with the 0.1 nF output capacitor fitted.
- Clone power rail: identify the clone and check what P0.13 does on it. On the genuine nice!nano it switches VCC with high meaning off. SuperMini-style clones use an LDO enable where low means off ([nrfmicro wiki](https://github.com/joric/nrfmicro/wiki/Alternatives/)). Also measure whether the VCC pin and the nRF VDD are the same rail, because the ADC reference and the sensor output both scale with their supply.
- Pulsed-power settling with 100 nF, 10 nF and no bypass capacitor: rail rise plus the 100 µs tPO, versus scan rate.
- Sensor power switch part: load switch IC or P-MOSFET, chosen after the coupon shows the inrush and rise time.
- Mux footprint: SSOP-24 (CD74HC4067SM96) is the plan; TSSOP-24 and SOIC-24 second sources need different footprints.
- Retention: the switch has no electrical pins. Choose a plate or case approach (Partial-Gauss uses a 3D-printed plate).
- Keycaps and case: low-profile MX-stem caps; enclosure TBD.
