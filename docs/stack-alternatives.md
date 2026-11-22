# Does the detached driver belong under the stick?

Keep the Sprintek driver remote for the first sensor-over-XIAO prototype. The selected mockup puts the stick palmward of the middle right thumb key, Lower, in plan view. In the physical stack the sensor is **above** the XIAO; it is not tucked beneath the keycap. Moving the driver into this stack could shorten the connection, but does not establish a smaller keyboard. Try a driver on the back of the carrier before raising the stick on a third top-side layer. Neither alternative is fitted or approved for fabrication.

## What the precedent establishes

The [builder’s assembly instructions](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero) identify the same 3.3 V detached SK8707-01-004. The sensor is soldered on top of a custom daughterboard, the detached driver on its underside, and the daughterboard assembly on headers over an RP2040-Zero. This is three electronic modules **plus an interposer**, not three PCBs pressed together. The stated minimum 5 mm is header-pin protrusion **before assembly**, not an interboard gap or final height. The author also reports shorts after using solder paste and a driver broken during desoldering ([build guide](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero)).

The [working keyboard demonstration](https://www.reddit.com/r/ErgoMechKeyboards/comments/1wln421/trackpoint_on_rp2040zero/) is evidence for the topology, not a test of Tapir’s thumb reach, wireless performance or plug path. Tapir uses a different controller with USB-C, an onboard BLE antenna and underside GPIO pads ([Seeed Plus specification](https://www.seeedstudio.com/Seeed-Studio-XIAO-nRF52840-Plus-p-6359.html), [Zephyr pad map](https://docs.zephyrproject.org/latest/boards/seeed/xiao_nrf52840_plus/doc/index.html)).

## How much plan space can move?

Use rectangles aligned with their long sides parallel, zero edge gap and no connector overhangs. XIAO: **20.955 × 17.78 mm** nominal Edge.Cuts box from the [Seeed Plus v1.1 KiCad archive](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip), consistent with its 21 × 17.8 mm catalog rounding. Sensor: **18.29 × 13.20 mm** from [Sprintek drawing p. 6](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6). Driver: **23 × 14.5 mm** interpreted from the combined drawing, cross-checked against the ±11.5 × ±7.25 mm outline in a [third-party driver footprint](https://raw.githubusercontent.com/larssont/ergogen-footprints/main/sprintek_sk8707_01_driver.js). These are rectangular planning envelopes, not exact material areas.

| Arrangement | Ideal projected rectangles, no service clearances | Where the space goes |
|---|---|---|
| Three modules side-by-side | Areas sum to **947.51 mm²**. One simple zero-gap row fits a 45.48 × 23 mm box; this is not an optimal packing proof. | All three sites require plan area, but none has to sit above the USB connector or antenna. |
| Sensor over XIAO; driver elsewhere | Aligned sensor fits wholly inside 20.955 × 17.78. XIAO + remote driver total **706.08 mm²** in separate rectangles. | Ideal reduction of 241.43 mm² versus three nonoverlapping modules. Actual sensor offset, load-bearing feet, wiring and the RF exclusion grow the local envelope. |
| Sensor, driver and XIAO centered | Smallest aligned enclosing rectangle is **23 × 17.78 = 408.94 mm²**. The ideal projected union is **402.23 mm²**: XIAO plus (23 − 20.955) × 14.5 of driver; sensor fits inside. | The third layer recovers **303.85 mm²** of ideal projected union versus two sites. The tower grows 2.045 mm along the controller’s long axis, about 1.02 mm at each end when centered. |

In other words, the driver can share most of the XIAO’s shadow, not all of it. Centering is a packing exercise only: it deliberately ignores two ends that matter in a product, the plug approach and the antenna. Do not treat 23 × 17.78 as a mountable keep-out, daughterboard size, or case dimension.

### Baseline outline versus selected middle-thumb mockup

The following subtraction concerns **only the separate-site baseline**, not the selected middle-thumb bridge. It uses the thumb preset of `workbench/layout.js` (Choc, straight columns, no added column gap, neutral thumb offsets, 24 mm split). In the second calculation only the driver’s padded rectangle was omitted from the palm hull: remove the term `rect(driver, driver.w + 4, driver.h + 4)`, recompute the same bank/palm union, then compare XY extrema and shoelace areas. No file change or alternative assembly is needed to repeat the comparison.

| Right carrier contour | Local X range | Local Y range | Area |
|---|---:|---:|---:|
| Baseline outline, remote driver at (55, 39) | −34.075 to 100.750 mm | −30.250 to 76.100 mm | 11,319.82 mm² |
| Omit driver hull points only | Identical | Identical | 10,542.48 mm² |

That is **777.34 mm² less baseline right carrier area (6.87%), zero change in span**. The baseline hull fills the wedge between the driver, keys and thumb lobe, which explains why the contour difference exceeds the 333.5 mm² driver rectangle. Right-half bounds stay 134.825 × 106.35 mm; full layout at this split stays 293.649 × 106.35 mm. Finger/outer-column and thumb geometry set the extremes, not the driver at (55, 39).

The **selected middle-thumb mockup** is a separate run of `stackModel` with `headAcross:28, headShift:-2, offsetX:6, offsetY:-2, gap:0.8, orientation:'palm', sensorFlip:true`. Its shaft lies at local (8, 66) mm, 22.27 mm from the Lower key center; the USB mouth faces the palm edge. With the driver still remote, the model adds **258.14 mm²** of right carrier material versus the baseline but keeps the same **134.825 × 106.35 mm** bounds. Its 31.59 mm sensor-pad-to-driver distance is a straight-line lower bound, not a routed lead length or electrical test. Do not subtract 777.34 from 258.14: a three-module candidate needs its own perimeter and support geometry before any net area saving can be reported.

## What it costs in height

**Physical material floor:** The [sensor drawing](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6) gives 0.8 mm PCB plus 2.4 mm exposed stock post: 3.2 mm to its bare tip. The [Seeed KiCad file](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip) specifies nominal 1.6 mm board thickness and a four-copper-layer stackup; this is a design-file nominal, not a sample measurement. Let d be the detached driver’s **bare** board thickness, not the 3.0 mm populated keep-out. For stacked, parallel boards to the stock post tip, the material-only floor is **4.8 mm** for XIAO + sensor and **4.8 + d mm** for all three, before bridge, solder, components, insulation, rubber, host carrier or case. A side-by-side construction has a local floor of max(3.2, 1.6, d), not their sum. No detached driver thickness or populated maximum is established by the sensor side view; measure d and component peaks on the actual revision.

For a more useful comparison, take one explicit Tapir bridge setting: 5.0 mm mounted XIAO envelope, 0.8 mm free to the bridge, 0.8 mm bridge, 0.15 mm sensor attachment, 0.8 mm sensor, 2.4 mm post, 1.1 mm modeled cap above the bare tip. All values except sensor PCB and stock post are **model allowances** here. Z = 0 at the host carrier top. These are back-of-envelope examples, not alternative solids or new fit results:

| Location of driver | Result at this setting |
|---|---|
| Remote on top, sensor over XIAO | Stock tip Z +9.95 mm, cap Z +11.05 mm; **15.85 mm** from cap to a back sheet ending at Z −4.80. For comparison, the separate-site thumb baseline is 17.20 mm with its deeper cover for the underside sensor. |
| On underside of sensor bridge, above XIAO | The provisional 3.0 mm populated driver cannot occupy a 0.8 mm slot intact: **2.2 mm interference** if its envelope overlays the controller. Lift the bridge 3.0 mm to retain 0.8 mm beneath the driver: cap Z +14.05 and **18.85 mm** overall. Driver solder/standoff is extra if not already within that 3 mm. A face map could permit nesting; an empty-box render cannot establish it. |
| On reverse of carrier, below XIAO/bridge area | Keep the top-side stick elevation. The −1.6 mm carrier underside to −3.8 mm cover inside leaves **2.2 mm**. A 3.0 mm populated driver + 0.4 mm cover gap needs 3.4 mm: deepen a local right-hand pocket by **at least 1.2 mm** before attachment/tolerance. With a 1 mm cover the pocket bottom is Z −6.0, giving **17.05 mm** cap-to-pocket span. A flat full-width cover would impose that depth elsewhere too. |

The selected middle-thumb mockup uses this 0.8 mm bridge clearance with the driver remote; it is not a measured clearance. Increasing the free gap changes the interference calculated for the hypothetical third layer. Moving the driver below the carrier instead places copper and hardware on the other side of the radio. Consider that reverse-side scheme only if both board faces remain landable and the carrier, not the XIAO connector, takes pointing loads.

## Prototype gate

1. **Trace the real hardware.** Measure the driver thickness, both populated faces, solder fillets and pad access. Trace the actual USB shell/mouth, plug overmold and antenna in the [Plus files](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip). Record the exact revision; do not import the RP2040 header pattern or infer an antenna keep-out from a photo.
2. **Test the stack and its assembly sequence.** With existing samples or passive coupons, compare remote, driver-under-bridge and driver-under-carrier at the same shaft target. Use an independent load path, insulation and a removable driver. Fully mate and withdraw the intended cable, press adjacent keys to bottom-out, exercise pointing in both axes, close the cover and demonstrate that the driver can be installed and removed. Record minimum gaps including measured deflection and fabrication tolerance; reject any contact, shaft rub, preload or unserviceable joint.
3. **Make the wireless decision with evidence.** Compare closed-case split/BLE stability, reconnection and idle behavior against the remote-driver baseline with the same battery, orientation and host; test while pointing and when USB is used. Instrument the actual sensor-to-driver connection as routed and check drift, noise and response. The short path avoids a remote interconnect only if its pads really reach the interposer; a freehand connection length or passing CAD RF screen is not a qualification.
4. **Promote only for a measurable gain.** Report right-half width, depth, cap-to-lowest-point height and carrier area together, at the same thumb reach. Keep the remote driver if the only win is projected board area while the case gets taller or the USB/RF/service gates fail. No hardware was ordered, fabricated or physically validated for this comparison.
