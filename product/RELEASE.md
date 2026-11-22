# Rev A prototype decision

Disposition: **HOLD**. No fabrication, purchase or real-cell charging authorization. Digital results apply only to the named input files. No physical first article has been built or tested.

## Scope and evidence

70 pass digital · 1 blocked · 9 physical pending. See the [per-check and per-component report](validation/REPORT.md), [machine-readable results with input hashes](validation/results.json) and [bench acceptance card](validation/BENCH.md).

| Hand | Carrier envelope (mm) | Modeled assembled envelope excluding cable (mm) | Native copper |
| --- | ---: | ---: | --- |
| Left | 134.82 × 97.08 | 143.51 × 106.85 × 20.35 | [445 segments, 27 vias](electronics/reports/tapir-left-routing.json) |
| Right | 134.82 × 106.35 | 145.03 × 116.31 × 20.35 | [392 segments, 30 vias](electronics/reports/tapir-right-routing.json) |

The assembled bounds include the printed parts, populated boards, keycaps, controls, battery and fasteners, but not a mated cable, optional feet or manufacturing variation. Native motion checks and assembly STEP/STL files are in the build package. A [named Qualtek USB-C cable drawing](https://www.qualtekusa.com/images/Cable%20Assemblies/PDF_2/3021091-01M.pdf) anchors the external plug study; it cannot certify the real latch, insertion stop or electrical contacts.

## What keeps the build on hold

| Check | Status | Observation |
| --- | --- | --- |
| charger.voltage-compatibility | BLOCKED | BQ25100 regulation can reach 4.23 V; pack specifies 4.20 V CC/CV, with no approved +30 mV charging window. A PCM overvoltage trip is NOT a permitted CV limit. Obtain written pack compatibility for the full tolerance or redesign the charger; USB-only testing with both cells disconnected. One good measured unit is not qualification. |
| physical.mounts | PHYSICAL_PENDING | M01/M03: actual bores, fastener/tool access, bridge load/retention and removal are unmeasured. |
| physical.stroke | PHYSICAL_PENDING | M02/M06: 42 physical switches + caps, 3 buttons, thumb reach and simultaneous presses not exercised. |
| physical.usb | PHYSICAL_PENDING | M04: no actual USB overmold, mating stop or closed-case cable measured on either half. |
| physical.pouch | PHYSICAL_PENDING | M05: actual maximum pouch/PCM/wires, swelling, insulation and safe closure unverified. |
| physical.polarity | PHYSICAL_PENDING | E01/E02: board J1 pin allocation is intent. Exact Adafruit 1570 drawing calls for a reversed plug; verify real pack polarity with meter before connecting, never infer from colors. |
| physical.charge | PHYSICAL_PENDING | E02: physical 50 mA mode and peak below 100 mA through reset, DFU, USB hot-plug, suspend and charge termination not measured. |
| physical.power | PHYSICAL_PENDING | E03/E04: rail startup and backfeed, both battery-only current integrals, sleep/wake and seven-day runtime not measured. |
| physical.rf | PHYSICAL_PENDING | E05: closed-case BLE range/reconnect, hand attenuation and loss under load unmeasured. |
| physical.hid | PHYSICAL_PENDING | H01–H04: real host USB/BLE, cross-half drag and scroll, disconnects and recovery not exercised. |

Review the [part-by-part BOM](sourcing/bom.csv), [sourcing exceptions](sourcing/qualification.md), [pointing harness](electronics/pointer-harness.md), and the [power and functional acceptance plan](validation/BENCH.md). Do not count a datasheet allowance, a shelf listing or a USB simulator run as a physical sample measurement.
