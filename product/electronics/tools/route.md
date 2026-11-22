# Reproduce and inspect the carrier routing

Run the placement and schematic generators first. `build/<hand>/tapir-<hand>.kicad_pcb` is a disposable, placed carrier; `<hand>/tapir-<hand>.kicad_pcb` is the editable routed design. The output board, colocated schematic, local library tables and KiCad project must be kept together.

## Local toolchain

- **KiCad:** 10.0.8 with its Python `pcbnew` bindings. On Ubuntu 26.04 the system `/usr/bin/python3` imports these; a virtual environment may not.
- **Initial routing:** Java 25, local [FreeRouting v2.5.0](https://github.com/freerouting/freerouting/releases/tag/v2.5.0) for left and the independently tested [FreeRouting v2.1.0](https://github.com/freerouting/freerouting/releases/tag/v2.1.0) for right. Release JAR SHA-256: `f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7` (2.5) and `2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def` (2.1). No online routing service was used.

From the repository root, replay the accepted copper without a Java installation or internet connection:

```sh
/usr/bin/python3 product/electronics/tools/route_finish.py left right
```

Both final Specctra session files are checked in under `product/electronics/routing/`. The right session includes a manual inboard adjustment to the adjacent PS2_RST and PTR_EN diagonal corners, 0.020 mm and 0.025 mm along their Cartesian endpoint axes respectively, at the concave board edge. The left session had 46 segments narrower than their desired width; replay restores every segment to its project netclass width and runs DRC on the actual wide copper. All footprint records are kept byte-for-byte from the placement source, including the rotated switches/diodes; a grid conversion must never alter the land pattern.

To explore a different route rather than release the checked-in session, use the following scratch workflow (not a replacement for the accepted session):

```sh
export FREEROUTING_JAR=/absolute/path/to/freerouting-2.5.0.jar
for hand in left right; do
  /usr/bin/python3 product/electronics/tools/route_board.py "$hand" \
    --output "product/electronics/build/experimental-$hand/tapir-$hand.kicad_pcb"
done
```

Inspect the exported Specctra project in `build/route-<hand>/`. The DSN is emitted by KiCad from physical pads, drills, the board outline, copper rule areas and net classes. The SES contains routed copper that is imported by KiCad; no traces are inferred from an illustration. The native and router manufacturing layers are F.Cu and B.Cu. Parallelization, router heuristics, version or placement changes may produce different track geometries; verify the actual saved board each time.

## Release gates

`route_finish.py` replays the accepted sessions into fresh scratch projects and runs native `kicad-cli pcb drc --schematic-parity --all-track-errors --severity-all --exit-code-violations` before adding planes. The trace-only reports are kept under `../reports/hard-route-only/`. It then fills solid GND returns on both layers, removes isolated islands, retains the extra antenna-end pour exclusion and original placement, and checks the actual copper again before promotion.

`route_verify.py left right` independently rechecks the saved native projects. It rejects project DRC exclusions, checks original versus routed pad geometry and net membership, and counts physical trace segments, lengths and through-vias. Native DRC JSON and per-board routing summaries are in `../reports/` relative to this document. A DRC finding, mismatched pad, missing schematic or unrouted net is not a pass.

Do not interpret closed digital gates as assurance of RF performance, current, switching behavior, physical fit, solder quality or thermal capacity. Inspect native footprints, solder and mechanical clearances, probe actual assemblies and complete the separate prototype acceptance procedure before release.
