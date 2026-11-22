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
dimensional references, and open **Fit report** for signed envelope clearances.
Try both splay and gap at zero to see interference. Export the SVG at 100%
and check its 50 mm line with a ruler before testing reach. Key legends show
orientation; the workbench is not a firmware/keymap preview.

## Under-mounted pointing stick

The default is straight columns with a 6.5 mm added gap and a sensor board
2.8 mm below the carrier underside. Switch to **On top** without moving the
columns to see why the previous mount clashes, or choose **Original 16°** to
restore the previous layout. **Inspect underside** hides the back cover;
the live section shows how much longer the shaft and enclosure must be.

With Choc v1 the straight candidate has 1.0 mm from the proposed cap to the
nearest keycap, 0.5 mm from the reserved sensor volume to adjacent switch-back
envelopes, and an 18.6 mm nominal assembled height. These are model outputs,
not toleranced dimensions. This study assumes direct-solder Chocs, no socket,
matched back-cover planes and an unverified coupler. Before ordering, test two
adjacent switches, the real sensor, and an extension in a small carrier coupon:
verify bottom-out, tip leverage/drift, retention and routing with real solder joints.

Use `npm run build` in `workbench/` for the static site (`dist/`).
The 3D scene, vector fallback and print export share `layout.js`.
See [AGENTS.md](AGENTS.md) for the PCB, enclosure, firmware and prototype
acceptance process, including how to distinguish sourced dimensions from
unverified design allowances.
