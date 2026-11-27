# Tapir Rev A configuration freeze

Native product files under `product/` are authoritative for Rev A. The workbench's older thumb and stack placements are comparisons, not interchangeable build configurations. Changes to a footprint, connector, charge mode, mount or pin need the owning engineer to update the other domains and re-run the relevant gates before changing this record.

| Decision | Interface to preserve | Rationale / alternative |
| --- | --- | --- |
| Flat split, identical logical Corne order | 21 typing positions per hand; three added left mouse controls. Geometry uses local X right, Y toward the palm, Z from PCB top. No post-export mirroring. | One model supplies switch rotations, native board placements, case holes and diagrams. |
| 3.3 V Sprintek SK8707-01-004 over right XIAO near middle thumb | Support into carrier/case, not through the radio or USB shell; keep driver separate. | Original under-mount is the fallback. A ThinkPad donor does not have verified stock geometry, idle current or plug compatibility. |
| Seeed non-Sense XIAO nRF52840 Plus 102010672 | No 2.54 mm tall headers. D0–D3 rows, D4–D9 columns, right D10 data, D11 clock, D12 reset and D13 switched-rail enable. | Keep underside pads electrically and mechanically buildable. Used as separate wireless keyboard MCU, not the TrackPoint driver. |
| [Adafruit 1570 protected 100 mAh pack](https://www.adafruit.com/product/1570) | Use factory terminated PH lead; no live battery splicing. Leave 50 mA charge-rate selection in default high-impedance mode; verify worst-case current and pack rating. | Catalog dimensions 11.5 × 31 × 3.8 mm plus cable/plug, not generic 301230. Confirm polarity before ever mating a physical cell. |
| PCB-mounted JST S2B-PH-SM4-TB(LF)(SN) and C&K PCM12SMTR | One per half; plug accessible for service with lid off; side-actuated battery isolator; USB can still power the electronics with cell switched out. | No additional pigtail or 3814, no JS102 substitution. The [PCM drawing](https://www.littelfuse.com/assetdocs/littelfuse-ck-slide-pcm-series-datasheet?assetguid=d2f6a96c-7a9a-4c4e-a5aa-5fe3075dffe5) specifies its mounting pattern; the physical switch must align with that pattern and the enclosure opening. |
| Choc v1, direct solder, 1U MBK | Ordinary 18 × 17 mm pitch. Thin solder-tail envelopes, not hot-swap socket envelopes. | Hot-swap and PG1316S are separate designs. Off-the-shelf parts are favored; custom carrier and enclosure are intentional. |

No DRC, continuity or CAD pass substitutes for real battery polarity, charge current, antenna behavior, plug insertion, case assembly, pointing comfort or drop/travel durability. The release record must say which of those are still open.
