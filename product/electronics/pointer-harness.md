# SK8707-01-004: detached head to driver

**The remote head needs four independent analog connections, not five PS/2 wires or an eight-way FFC.** A photographed build using the [exact SK8707-01-004, detached, 3.3 V](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/README.md) identifies both assemblies. Its [routed, native KiCad adapter board](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/trackpoint_on_rp2040zero.kicad_pcb) physically joins four sensor lands to four wide driver lands. This is credible **connectivity and orientation** evidence, not a manufacturer specification for remote cable length, bridge polarity or permissible mechanical load. Tapir has not physically tested this harness.

## Wiring map and orientation

Set the **sensor stem upward**, its long dimension vertical on the page and its notched, castellated short edge at the **bottom**. The four land groups read left to right. The first two groups each have one contact; the last two each have **two copper sections that must land on the same corresponding adapter pad**. Six solder joints make four electrical channels. See the [pre-solder head photo](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/images/sensor_before.jpg), [soldered head](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/images/sensor_after.jpg) and [holykeebs Step 5](https://docs.holykeebs.com/guides/trackpoint-module/). Do not count the side cut-outs or four corner attachment holes as signals.

Set the **driver populated IC face upward**, its four broad analog castellations along the **bottom** and its eight smaller host castellations along the **top**. The end of the host row containing manufacturer Method 1 pin 1/GND is on the **right** in this orientation: compare the [builder's driver photograph](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/images/driver_after_2.jpg) (U1 visible, `J1`/corner hole toward the host pin-1 end) with [Sprintek DS0048 v1.04, pp. 3–4, 6](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=4). It is not the eight flat FFC solder fingers on the driver's face. The absolute reference is the **four-wide-pad end nearest the Method 1 host-GND end**, not lettering assumed to survive a hardware revision. In these two deliberately defined face-up views, **sensor leftmost goes to driver rightmost**.

| Tapir analog conductor (label both ends) | Head: stem up, castellations at bottom | Driver: IC up, four wide pads at bottom | Published reference land/net |
|---|---|---|---|
| A1 | Group 1, far left, single | Rightmost, nearest the host pin-1/GND end | `Sn1 → Dr1`, `TP_SN1` |
| A2 | Group 2, second from left, single | Second from right | `Sn2 → Dr2`, `TP_SN2` |
| A3 | Group 3, third from left, both halves | Second from left | `Sn3 → Dr3`, `TP_SN3` |
| A4 | Group 4, far right, both halves | Leftmost, farthest from the host pin-1/GND end | `Sn4 → Dr4`, `TP_SN4` |

This is a position-to-position map from [the adapter's actual pads and copper](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/trackpoint_on_rp2040zero.kicad_pcb) and [its pinned footprint generator](https://codeberg.org/humanplayer2/ergogen_footprints/src/commit/3e219084235f1bbccb88213863e37c6a4ea0cf3d/trackpoint_on_rp2040zero.js). `Sn1`, `Dr1` and A1 are **not Sprintek pin numbers**. The generator's uppercase `Dr1` is the first analog input; its lowercase `dr1` is host-side GND on the opposite edge. They must never be connected to each other. No source here establishes which bridge node is excitation, reference, sense, X, or Y; do not apply a test voltage to A1…A4. As an independent layout cross-check, the [larssont sensor footprint](https://github.com/larssont/ergogen-footprints/blob/708940922192a481cd40c6cef9ae80de49a9e104/sprintek_sk8707_01_sensor.js) and [driver footprint](https://github.com/larssont/ergogen-footprints/blob/708940922192a481cd40c6cef9ae80de49a9e104/sprintek_sk8707_01_driver.js) also use four sensor nets, place TPS1 closest to the host-GND end and number pads differently. Never port those library pad numbers without their local layer/flip transforms.

## Build datums, mount and egress

- **Head:** The [Sprintek mechanical drawing, p. 6](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6) puts the physical contact edge 10.84 mm from the post axis. Relative to that axis, the four adapter land centers span transverse X = −3.75, −1.25, +1.25, +3.75 mm. In the reference board, lands extend beyond the sensor edge for a visible solder fillet; their centers are 0.25 mm beyond the drawn sensor perimeter. The 13.2 × 18.29 mm head has four holes on 9.50 mm square centers. The exact -004 is supplied **without metal plate**, not the threaded-plate assembly also illustrated in the family datasheet.
- **Driver:** The four broad edge contacts are opposite and distinct from the eight small host castellations. The reference footprint's driver outline is 14.5 × 23.0 mm. In its drawing, analog land-center separations are 2.50, 2.50, **2.30** mm; the author explicitly applies −0.20 mm in the [generator](https://codeberg.org/humanplayer2/ergogen_footprints/src/commit/3e219084235f1bbccb88213863e37c6a4ea0cf3d/trackpoint_on_rp2040zero.js). This is a builder-measured footprint tweak, **not** a guaranteed Sprintek pitch. Align a sample to a 1:1 coupon before freezing copper.
- **Reference versus Tapir:** The [reference assembly](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/README.md) solders the driver on the bottom of one rigid adapter, sensor on top, then uses RP2040 header pins for support. The four analog connections there are short PCB traces, **not a demonstrated flying cable**. In [holykeebs Steps 2–6](https://docs.holykeebs.com/guides/trackpoint-module/) the four sensor holes have separate mechanical attachment to the support; do not count the signal fillets as the thumb-load path. Tapir's bridge must bear load to the carrier/case, not through the radio, USB shell, sensor traces, or solder tails.
- **Tapir termination proposal, not released:** Use supported breakout lands at the head's notched short edge to gather the two split groups correctly, and a separately supported termination at the driver's four-wide edge. Label the four conductors at both terminations. Reserve space beyond both edges for fillets, insulation and a slack service bend before fixing the cable to a nonmoving support; keep it clear of key travel, the cell, USB sweep, antenna region and closure screws. Do not glue the active flexing region, use the analog wires as a tether, or assume the four holes accept threaded M2 fasteners. Wire construction, bundle size, stiffness, free length, shield requirement, strain relief and actual egress/turn radius are **still unqualified**. A line in CAD or a clearance fit cannot settle those questions.
- **Separate host harness:** Tapir right J2 (five wires) runs **driver to carrier** using the [Method 1 castellated host definition](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=3): pin 1 GND, 2 DATA, 3 CLK, 4 active-high RESET, 5 switched VCC. The builder's example used only GND, DATA, CLK and VCC plus separate header support, not Tapir's driven reset. The order on the alternative FFC host interface is different. Neither host pinout describes head wiring.

## Reproduce the reference trace

The source release has a routed PCB and Ergogen input, not a standalone schematic. The native board SHA-256 is `8c5f69050aab5bf7bfd2df89f31def6d04e88bf6288147d4740fb4d9905ef43c`. These are **adapter-local coordinates** from the [published PCB](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/trackpoint_on_rp2040zero.kicad_pcb), not Tapir positions. Use front-view KiCad XY with +Y down for both copper layers; origin is the adapter footprint anchor at board (110,90). The driver is mounted on the back, so merely comparing two photographed faces without a mirror/turn is wrong.

| Net | Sensor F.Cu local XY | Through-via local XY | Driver B.Cu local XY |
|---|---|---|---|
| `TP_SN1` | (−3.75, 22.25) | (+0.60, 16.20) | (+7.60, 15.20) |
| `TP_SN2` | (−1.25, 22.25) | (+2.60, 13.70) | (+7.60, 12.70) |
| `TP_SN3` | (+1.25, 22.25) | (+4.60, 11.20) | (+7.60, 10.20) |
| `TP_SN4` | (+3.75, 22.25) | (+5.60, 8.90) | (+7.60, 7.90) |

Each route is one front trace, one plated via and one back trace. The reference sensor pads are 1.2 × 1.5 mm; driver pads are 1.5 × 1.2 mm. In the same coordinates the separate digital `dr1` GND pad is (−7.60,19.42), proving which end of the analog row is nearest the GND end. These coordinates describe the builder's landings, not recommended pad dimensions for Tapir. To reproduce without copying the design into the product:

```sh
set -eu
D=$(mktemp -d)
REV=5ed40be68067f34ef245e602ef3df02ccc7fffdc
BASE=https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/raw/commit
curl -fsSL "$BASE/$REV/trackpoint_on_rp2040zero.kicad_pcb" -o "$D/adapter.kicad_pcb"
printf '%s  %s\n' 8c5f69050aab5bf7bfd2df89f31def6d04e88bf6288147d4740fb4d9905ef43c "$D/adapter.kicad_pcb" | sha256sum -c -
kicad-cli pcb drc --severity-error -o "$D/adapter.rpt" "$D/adapter.kicad_pcb"
# Debian/Ubuntu KiCad's system Python includes pcbnew.
/usr/bin/python3 - "$D/adapter.kicad_pcb" <<'PY'
import sys, pcbnew as k
b = k.LoadBoard(sys.argv[1])
xy = lambda p: tuple(round(k.ToMM(v), 3) for v in (p.x, p.y))
for i in range(1, 5):
    net = f"TP_SN{i}"
    pads = {p.GetNumber():p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()==net}
    assert set(pads) == {f"Sn{i}", f"Dr{i}"}
    s, d = pads[f"Sn{i}"], pads[f"Dr{i}"]
    assert s.IsOnLayer(k.F_Cu) and d.IsOnLayer(k.B_Cu)
    tracks = [t for t in b.GetTracks() if t.GetNetname()==net]
    assert len(tracks)==3
    via, = [t for t in tracks if t.GetClass()=="PCB_VIA"]
    v = xy(via.GetPosition())
    for layer, pad in ((k.F_Cu,s),(k.B_Cu,d)):
        tr, = [t for t in tracks if t.GetClass()=="PCB_TRACK" and t.GetLayer()==layer]
        assert {xy(tr.GetStart()),xy(tr.GetEnd())} == {xy(pad.GetPosition()),v}
    print(net, xy(s.GetPosition()), v, xy(d.GetPosition()))
PY
```

Running KiCad 10 on that isolated upstream file gave **0 unconnected pads**, but also **12 copper-to-edge errors** against the default 0.50 mm rule, including the four intentional edge landings. This is not a clearance waiver for Tapir or a recommendation to fabricate the reference unchanged. There is no Tapir sensor interposer Gerber or manufacturer-approved analog cable in this evidence.

## Physical acceptance before first power

1. Verify both actual pieces are the -004 3.3 V detached pair, photograph their faces with a scale, mark the head's two split groups and the driver's eight-small/four-wide sides, and record its Method 1 pin-1 end against the [Sprintek pin-1 figure](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=4). If the outlines or fiducials differ, stop and identify the revision instead of guessing.
2. Test the **unloaded, disconnected harness/interposers** with a meter: A1→A1 through A4→A4, no cross-pairs/shorts, no analog-to-host or bracket contact; photograph both end labels for continuity records. Do not demand infinite resistance between neighboring contacts on the **connected** resistive sensor or powered driver; the bare-harness check is distinct. Do not inject supply voltage into any analog node.
3. Seat sensor and driver independently, inspect all six sensor wettings onto four lands and all four driver joints under magnification, clean and check the underside for contamination. Confirm no preload at neutral, no solder-joint tension when servicing, and no compression, loosening, chafe, or motion interference with the case closed. The builder describes both [driver damage on rework and flux-induced shorts](https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero/src/commit/5ed40be68067f34ef245e602ef3df02ccc7fffdc/README.md).
4. On a restrained bench fixture, apply current-limited power **only to the verified host side**, then compare a short known-good connection with Tapir's intended cable. Record current, neutral drift/noise, all four signed directions, return-to-zero, cable flex and button/key activity, BLE/USB operation and sleep/wake. Record conductor type, free length, orientation and strain-relief photos with results. Until both wiring and the fitted dynamic tests pass, the remote harness remains a release blocker, not a populated-board DRC success.
