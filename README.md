# Tapir

Tapir is a low-profile wireless split keyboard concept with 42 typing keys,
a right-hand pointing stick at the inner end of the thumb cluster, and
left-hand click and scroll controls. The first prototype is an interactive
geometry study, not manufacturing CAD.

## Try the assembly workbench

With Node.js 20.20 or 22 LTS and npm, run from the repository root:

```sh
cd workbench
npm ci
npm run check
npm run dev
```

Open the local URL printed by Vite. Adjust splay, the gap, and the stick's
position beside the thumbs; compare Choc v1 with PG1316S. Inspect a part for its
dimensional references, and open **Fit report** for signed envelope clearances.
Move the thumb stick 4 mm away from the palm to see a nominal collision. Export the SVG at 100%
and check its 50 mm line with a ruler before testing reach. Key legends show
orientation; the workbench is not a firmware/keymap preview.

## Right-thumb pointing stick

Inspired by [Dabao's thumb placement](https://github.com/justinmklam/dabao),
the default puts the nub 15 mm toward the palm from the innermost right thumb
key center. All six thumb keys stay put. The finger bank returns to standard
18 × 17 mm Choc spacing, with no splay or extra gap. The underside sensor is
rotated across the thumb bay with 1.4 mm between its top and the carrier underside.
The detached driver stays in its previous position. The three older inter-column
presets are retained for comparison.

**Compare thumb reach · 1:1** exports two right-hand patterns on one A4 sheet.
Print at 100% and verify the 50 mm rule: can the thumb steer the nub without
lifting the palm or bumping a thumb key? Use the two thumb offset sliders to
move the axis and print again. **Export full layout** still produces both halves.

The reference geometry is the Sprintek SK8707-01-004; salvaged two-piece
ThinkPad assemblies from AliExpress are legitimate candidates. See
[pointer sourcing](docs/pointer-sourcing.md) before buying a T440 donor
or cutting a footprint for it. The workbench does not assert donor fit.
Test retention, electrical pinout, consumption and drift on the actual sample.

Use `npm run build` in `workbench/` for the static site (`dist/`).
The 3D scene, vector fallback and print export share `layout.js`.
See [AGENTS.md](AGENTS.md) for the PCB, enclosure, firmware and prototype
acceptance process, including how to distinguish sourced dimensions from
unverified design allowances.
