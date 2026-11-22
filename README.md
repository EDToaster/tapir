# Tapir

Tapir is a low-profile wireless split keyboard concept with 42 typing keys,
a right-hand pointing stick between the fourth and fifth columns, and
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
fore/aft position; compare Choc v1 with PG1316S. Inspect a part for its
dimensional references, and open **Fit report** for signed plan clearances.
Try both splay and gap at zero to see interference. Export the SVG at 100%
and check its 50 mm line with a ruler before testing reach. Key legends show
orientation; the workbench is not a firmware/keymap preview.

Use `npm run build` in `workbench/` for the static site (`dist/`).
The 3D scene, vector fallback and print export share `layout.js`.
See [AGENTS.md](AGENTS.md) for the PCB, enclosure, firmware and prototype
acceptance process, including how to distinguish sourced dimensions from
unverified design allowances.
