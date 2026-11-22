# Tapir

Tapir is a flat wireless split keyboard designed around the 42-key Cygnus/Corne layout. There are three rows of six and three thumbs per half. A separately supported Sprintek pointing stick sits over the right XIAO near the middle thumb. The three extra controls on the left are for left click, right click and hold-to-scroll. Nothing replaces a typing key.

**Rev A is a digital prototype on hold, not an approved hardware build.** Start with the [engineering handoff](product/README.md), [release evidence](product/validation/results.json), [physical acceptance procedure](product/validation/BENCH.md) and [configuration decisions](product/design-decisions.md). Do not connect or charge a cell until the battery gates are closed. No physical fit, runtime, radio range or charging result is claimed.

## Inspect the design

The [assembly workbench](https://www.perplexity.ai/computer/a/06720a1c-6b0b-43b8-b744-eb15799f3c35) opens the Rev A product. Select a half to inspect carrier insertion, bezel closure or a named USB-C plug gauge. You can also rotate the assembly, switch to plan or front view, toggle layers, or separate parts along the board normal. The dimension cards distinguish the complete modeled assembly from the smaller bare PCB. The product uses separate left/right geometry; neither final half is a mirrored copy of the other. Download the build package there for the editable design and generated deliverables.

To run or rebuild the site from source:

```sh
cd workbench
npm ci
npm run check
npm run dev
# For the static deployment: npm run build
```

The basic web preview needs Node 20.20+ or 22 LTS and Python 3. The full preview also uses the KiCad 10 Python bindings, the generated build123d case mesh directory and the local STEP library. Follow the [native handoff](product/README.md) for those tools. Missing geometry is not replaced with guessed routes or checked-off results.

## Explore alternatives

Open **Design studies** for dimensional sliders, the 1:1 reach template and the earlier inter-column, under-mounted and stacked studies. Print at 100% and verify the 50 mm scale bar. These are comparisons, not alternative build configurations for the routed boards. The current Sprintek layout does not establish that a salvaged ThinkPad stick will fit or work electrically.

- [Thumb-placement and donor sourcing](docs/pointer-sourcing.md)
- [Stack mechanics and competing positions](docs/stack-mechanics.md)
- [Original RP2040-Zero inspiration and supplier drawings](docs/stack-evidence.md)
- [Earlier editable stack-only model](mechanical/stack/)
- [Project rules and authorization boundary](AGENTS.md)
