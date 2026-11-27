# Tapir Rev A: product and release criteria

Tapir is a flat wireless travel keyboard that replaces a separate mouse without making a Cygnus/Corne user relearn their 42 typing positions. The product baseline is Choc v1, a protected cell in each half, ZMK, and a separately supported Sprintek head above the right XIAO near the middle thumb. A commercial part number or a seller name is not evidence of physical compatibility.

## Acceptance contract

| Priority | User outcome | Acceptance test and release rule |
| --- | --- | --- |
| P0 | Type on familiar keys | Three rows of six plus three thumb keys per hand. Trace every physical coordinate through the matrix, diodes and devicetree into the existing Corne logical order and keymap. Exercise all 42 positions unambiguously; keep the three left pointing controls separate. |
| P0 | Use the computer without a mouse | Right-thumb pointing, left and right click, sustained drag, vertical scroll while holding the mode control, and return to ordinary pointing on release. Test USB and BLE, across split disconnect/reconnect, without stuck buttons. |
| P0 | Carry it without excess width or depth | No added finger-column splay or gap, 18 × 17 mm pitch. Target carrier bounding boxes at or below 135 × 107 mm per half; report shell, knob, feet and inserted cable separately. Do not optimize the bare PCBs while growing the case or extending reach without reporting it. |
| P0 | Buy reproducible components | Exact variant, installed quantity, orientation and supplier reference for every installed BOM line. Flag captive kits, uncertain live stock, cable/PCB revisions and alternates that need a footprint change. A salvaged TrackPoint is an option after measurement, not an interchangeable BOM substitute. |
| P0 | Operate safely on a small battery | Use the selected cell manufacturer's charge limits, protection and data for the chosen XIAO charge mode. Check polarity, rail behavior with USB, electrical overstress, isolation of an off pointer, and no reverse feeding. Block assembly if rated charge current cannot be established; a nominal mAh label is not a charge rating. |
| P0 | Have confidence in assembly | BoM vs. placed ECAD references, native ERC, routed PCB DRC and schematic parity; firmware built for both roles; native CAD, assembly order, shaft/plug/fastener and travel checks; register diagrams to the native coordinates. Every exclusion needs an owner and a residual risk. |
| P1 | Use a genuinely portable battery | Engineering target: at least 7 days per charge at room temperature with 1 h pointing, 7 h keyboard-connected and 16 h sleeping daily. At the [Adafruit 1570's catalog 100 mAh](https://www.adafruit.com/product/1570) and a provisional 80% usable fraction, this budgets 0.476 mA averaged over 24 h. Measure each half at its battery with USB removed. This is a target, not a runtime claim. |
| P1 | Reach and service the thumb control | At 1:1, reach the nub with the index finger on J, bottom all three thumbs, and try the actual USB cable without brushing the palm. With power off, remove the case without bending the cell or taking load through the USB shell. |

## Decisions and non-goals

Keep personal key behavior ahead of connector pin compatibility with a nice!nano. Prefer an orderable non-Sense XIAO Plus over an integrated bare radio in this revision: the latter changes assembly and RF validation. Keep cells accessible and directly supported; do not use the pouch as a spacer. Keep switch sockets and decorative lighting out of a thickness- and sleep-current-constrained first prototype. Keep the sensor driver remote unless a new CAD and electrical run proves an all-three stack is smaller as a complete assembly.

## What “tested” means

A reproducible numerical, CAD, electrical-rule or firmware-build result is a digital result only. Split antenna performance under a hand, real plug mating, housing and cap tolerances, pointing drift, tactile feel, current and charging all need a matching physical sample. No skipped test counts as a pass. No order, payment, paid runner, quote request or manufacturing submission is part of this release.
