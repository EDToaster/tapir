# Silkscreen patterns

Generative black-and-white artwork for keyboard PCB silkscreen, shared by every project in this repo. Each pattern changes across the board through flow, warping, density or scale, so no single tile repeats.

All SVGs are 400 × 250 mm with mm units in the viewBox. That covers any keyboard PCB, so you can place, scale and crop a pattern to your outline. Black is ink. The canvas has no background rectangle.

| # | Pattern | What varies | Ink |
| --- | --- | --- | --- |
| 01 | [Op-art ribbons](svg/01_op_art_ribbons.svg) | Bands swell and pinch around two lenses | 48% |
| 02 | [Flow field](svg/02_flow_field.svg) | Evenly spaced streamlines over curl noise | 23% |
| 03 | [Quadtree Truchet](svg/03_quadtree_truchet.svg) | Tiles subdivide toward two attractors, so arcs shrink and thin | 17% |
| 04 | [Reaction-diffusion](svg/04_reaction_diffusion.svg) | Gray-Scott feed/kill sweep: spots, then labyrinth, then holes | 44% |
| 05 | [Vortex grid](svg/05_vortex_grid.svg) | Square lattice pinched and twisted by three wells | 18% |
| 06 | [Vasarely bulge](svg/06_vasarely_bulge.svg) | Checkerboard inflated by two spheres | 50% |
| 07 | [Phyllotaxis ripples](svg/07_phyllotaxis.svg) | Golden-angle dots with concentric size ripples | 6% |
| 08 | [Hex morph](svg/08_hex_morph.svg) | Hexes grow from dots into rings, then solid cells, while rotating | 36% |
| 09 | [Marble bands](svg/09_marble_bands.svg) | Domain-warped stripes, thin lines to fat bands | 40% |
| 10 | [Circle pack](svg/10_circle_pack.svg) | Packed discs: rings, bullseyes or dots by size | 22% |

Low-resolution previews are in [preview/](preview/).

![All ten patterns](preview/contact_sheet.png)

## Fab limits

Strokes are at least 0.25 mm. Filled features and gaps are designed to be at least 0.3 mm, which clears the usual 0.15 mm silkscreen line minimum at JLCPCB and PCBWay. `check_widths.py` rasterizes each SVG at 0.05 mm per pixel. It reports the share of ink and gap pixels in features narrower than about 0.2 mm, mostly anti-aliasing and the pointed ends of tapering shapes. The last run found under 0.5% for every pattern.

Fabs remove silkscreen over exposed copper and drilled holes, so switch pads, hotswap sockets and the MCU footprint will cut gaps in a pattern. Busy fills like 04 and 06 also compete with reference designators and polarity marks. Keep those marks on the other side or clear a margin around them.

## Using a pattern in KiCad

1. In the PCB editor, choose **File → Import → Graphics**, pick the SVG, set the layer to `F.Silkscreen` or `B.Silkscreen`, and keep the scale at 1. In KiCad 7 and newer, filled patterns (01, 04, 06, 08, 09) import as filled polygons, and line patterns as graphic lines with their stroke width.
2. Move the import so the board sits over the part you want, then delete everything outside `Edge.Cuts`. You can also crop the SVG to your board outline in Inkscape first.
3. Run DRC. KiCad flags silkscreen over pads and outside the board edge.

The vortex grid and flow field contain tens of thousands of segments. If KiCad slows down, crop to the board in Inkscape before importing, or convert to a bitmap with the KiCad Image Converter.

## Regenerating

```sh
pip install numpy scipy matplotlib cairosvg pillow
python3 generate.py out                        # all patterns into out/ and out/preview/
python3 generate.py out flow_field hex_morph   # only the named patterns
python3 check_widths.py out
```

Each pattern is a seeded function in `generate.py`. To get a different variation of the same design, change its seed or attractor positions. Reaction-diffusion simulates 14,000 steps and takes about four minutes. The others take seconds.
