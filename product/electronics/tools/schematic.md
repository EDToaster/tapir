# Tapir carrier circuit and schematic gates

Open the same-stem `.kicad_pro` in either hand directory and open its sheet. Each A3 sheet is a single, editable, KiCad 10 circuit with local symbol/footprint libraries. Wires across the matrix form six independent column buses and four independent row buses: crossings without a dot do not join. Every diode bar is the cathode (pad 1) on its row. Do not connect the physically unused ROW3 positions on the right. Its three thumbs are on hardware COL3–5; the right firmware scan lists column GPIOs in reverse order.

The supply path is J1 pin 1 → S1 common → selected throw → U1 BAT+. The pack's pin 2 returns to U1 ground. S1 disconnects only the cell: USB and charging belong to the XIAO module, and switching off is not an assurance that the board cannot be powered by USB. The two logical `PWR_FLAG` annotations are on the cell return and switched feed at the actual connector/switch circuit, not blanket overrides of ERC. The right carrier takes regulated 3V3 from U1 into U2. QOD is tied to VOUT, CT is left open, and R3 holds ON low at reset. R1/R2 pull CLK/DATA to switched `PTR_3V3`, not the always-present module rail. Check RESET/GPIO behavior and off-state back-power on the bench; ERC verifies connectivity, not leakage.

On the right, land the five J2 leads on Sprintek's **Method 1 castellations**: 1 GND, 2 DATA, 3 CLK, 4 active-high RESET and 5 VCC. The top and bottom host FFC options (Methods 2 and 3) instead put GND and VCC on pins 7 and 8; the sensor flex is another interface entirely ([Sprintek DS0048 v1.04, pp. 3–4](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=3)). Do not blindly transfer pad numbers between these interfaces.

## Regeneration and verification

From the repository root, after the project/footprint and component-manifest generation steps:

```sh
python3 product/electronics/tools/schematic.py
/usr/bin/python3 product/electronics/tools/check_schematic.py
```

Use KiCad **10.0.8** and its matching `pcbnew` Python module. The first command reads `product/electronics/build/{left,right}/design.json`; the second runs native ERC at all severities with violation exit codes, exports XML with KiCad itself, and checks each exported terminal against the manifest, including pin type, connected net or explicit NC. Then it opens the final board through KiCad's board API and compares the footprint ID, value, symbol-instance path, and every numbered pad's net, including repeated numbers and NCs. Electrically empty board-only mounting footprints are enumerated. Native reports and digest-bound comparisons are written in `product/electronics/reports/`. Use `--schematic-only` before a PCB exists, or `left --board path/to/placed.kicad_pcb` to explicitly compare an intermediate board; neither is evidence that routed-copper DRC passed. Run the [routing checks](route.md) separately.

The native ERC JSON distinguishes project exclusions (none) from KiCad's built-in ignored categories. In this project these are single-use global captions, four-way junction advisories, SPICE model checks and footprint-filter advisories. The matrix's one-off branch labels name real nets independently checked pin by pin; a populated circuit simulation is not claimed. Each parity summary lists these categories explicitly.

## Hidden XIAO lands

Check the actual module artwork as well as the symbol-to-carrier netlist. Download the [Seeed Plus module board archive](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip) and [Seeed host footprint archive](https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip); the tool rejects archives with different hashes. Then run:

```sh
/usr/bin/python3 product/electronics/tools/check_xiao_lands.py /path/to/module.zip /path/to/host.zip
```

The checker registers the carrier host pattern to independent castellations in the manufacturer's module artwork; it does not fit the transform to the six pads it tests. Pads 24–27 align with TP5/SWDIO, TP3/SWDCLK, TP2/RESET and TP1/GND respectively. Pads 28/29 align with BAT0/VBAT and GND0/GND; their centres are displaced about 0.49 mm along the long axis, while their axis-aligned rectangles still overlap about 1.78 × 1.02 mm. See [the recorded pad-by-pad results](../reports/xiao-hidden-lands.json) for exact residuals. This is nominal, top-view CAD: no solder paste, wettable area, rounded-corner losses, manufacturing tolerances, or joint yield is guaranteed. For debug access, unused carrier debug lands are deliberately marked NC and the module's own USB recovery path is distinct.
