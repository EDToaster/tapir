# Working on Tapir

Tapir is a portable, flat, wireless split keyboard. Keep the familiar Cygnus/Corne
3×6 + 3 thumbs per half. Put the right-hand pointing stick beside the thumb
cluster without replacing any thumb keys; keep normal finger-column pitch and
zero splay by default. Inter-column configurations are comparison studies.
Design, simulate, render, and revise in Git without asking about each trace, hole, or
case iteration. **Stop before ordering PCBs, PCBA, printed parts, or components;
paid fabrication and purchases require explicit approval.**

## Product and study boundaries

- `product/` owns the Rev A deliverable. Read its README, design decisions, requirements, actual native reports and open acceptance gates. `product/design/geometry.json` is the common placement contract. Regenerate it from editable code; never realign board, case, illustrations or tests by moving individual projected elements.
- `workbench/layout.js` owns the original parametric layout, dimensions, plan clearances, and 3D underside-envelope checks;
  `workbench/parts.js` gives their provenance and limitations. The interactive workbench,
  vector fallback, and printable reach template consume the same layout. Keep them in sync.
- `workbench/stack.js` owns the optional sensor-over-XIAO study; keep its 3D,
  fit checks, 1:1 print, and the [build123d assembly](mechanical/stack/) on the
  same geometry. Regenerate its STEP when the selected model changes, not for
  unrelated UI changes. Do not count an overlapping RF screen as radio validation.
- Work in mm. Layout X is across the halves, Y increases toward the thumbs, and height
  is relative to the carrier PCB top. The Three.js renderer uses Y up, so layout Y maps
  to scene Z. Document the datum and transforms when moving to a production CAD coordinate system.
- Distinguish the `workbench/study.html` comparison scene from the native product viewer at `workbench/index.html`. The latter reads copper from the actual boards, enclosure meshes from build123d, and the release ledger from validation. Keep the no-WebGL fallback visibly labeled. A positive plan gap is not proof of 3D fit; do not call a placeholder a vendor model.
- From the repo root: `cd workbench && npm ci && npm run check && npm run build`.
  Use `npm run dev` there for the interactive model. When changing geometry, inspect both
  halves, top/front/exploded views, key-down state, a known overlap, and the 1:1 print scale.

## Parts and firmware constraints

- Use an exact manufacturer part number, revision/variant, and orderable supplier in the
  BOM. Salvaged modules from AliExpress are valid candidates: when no MPN is
  available, record the donor, seller, markings, photos and measurements of the
  actual sample. Do not assume that two parts sold under one laptop name share
  a bracket, pinout or idle current. Link the drawing, supplier STEP, or measurement record. Mark
  each critical value as **drawing**, **measured** (what and how), or **allowance**.
  Never silently replace missing geometry with a nominal package name. Flag single-source,
  discontinued, unverified, or out-of-stock parts before designing around them.
- Start from Choc v1 + MBK caps. Treat PG1316S as a different footprint, cap, and
  travel, not a drop-in swap. Model the Sprintek sensor, separate driver, cable, post,
  and rubber cap individually. A custom extension needs stiffness, travel, and drift tests.
- Start from the non-Sense **XIAO nRF52840 Plus** on each half. Keep its underside
  contacts landable, antenna clear, and USB-C accessible. Preserve left click, right click,
  click-drag, and hold-to-scroll while pointing; the left thumb controls must not
  replace typing keys. Use the 1:1 sheet to test reach before freezing the layout.
- Preserve the [Corne logical key order and behaviors](https://github.com/EDToaster/edtoaster-zmk-keymaps/blob/main/config/corne.keymap),
  not the nice!nano binary or electrical pin numbers. Check position-dependent
  hold-taps when adding buttons. Plan 4×6 matrix wiring (10 GPIOs per half);
  the three left mouse controls use spare intersections. Reserve four more GPIOs
  on the right for PS/2 clock, data, reset, and switched power. Verify pad access and
  pin conflicts against the actual board before routing.
- Build both ZMK roles from the project's [pinned firmware manifest](product/firmware/config/west.yml) and retain attribution to the original Corne keymap.
  Verify scan order, split roles, scroll and drag across halves, and sleep/wake without
  a stuck click. Budget pointer active, idle and off current, regulator and PCB leakage,
  and battery charging against the exact protected cell. Report runtime as an estimate
  until measured at the battery with USB disconnected.

## PCB and mechanical handoff

1. Once the design moves beyond the workbench, keep editable **KiCad 10** schematics,
   board and project-local footprints/models, and **build123d Python** for the enclosure.
   Pin tool/library versions and record the clean regeneration commands. STEP is for
   interchange; STL is for printing. Neither replaces the source. A wrapper CLI is optional.
2. Set the intended board house's stackup, copper/clearance, via and edge rules before
   routing. Use SPICE only to resolve a specific electrical question (e.g. the pointer
   power switch); record models, assumptions and acceptance limits.
3. Once KiCad source exists, set `SCH` and `PCB` to the actual schematic and board
   paths, create a build directory, and run these [KiCad CLI gates](https://docs.kicad.org/10.0/en/cli/cli.html):

   ```sh
   mkdir -p build
   kicad-cli sch erc --exit-code-violations -o build/erc.rpt "$SCH"
   kicad-cli pcb drc --schematic-parity --exit-code-violations -o build/drc.rpt "$PCB"
   kicad-cli pcb export step --subst-models --no-dnp -o build/populated.step "$PCB"
   ```

   Inspect missing/misplaced footprint models and mounting heights. Import the populated
   board into [build123d](https://build123d.readthedocs.io/en/stable/import_export.html);
   derive the case outline, holes and connector openings from that assembly, not a second
   hand-entered board. Keep any placeholder envelopes identified in the assembly.
4. Check the assembly **in motion**, not just at its final pose. Show a feasible board
   insertion/removal path past the pointer and switches; a real USB-C plug fully seating;
   the populated PCB seated with the battery, its leads and insulation clear; and the
   cover closing without compressing the pouch. Sweep adjacent keys to bottom-out.
   Include fastener/tool access, solder tails, cable bends, RF keep-out, cell allowance,
   and the intended printer's dimensional error and wall limits.
5. For prototype approval provide the revision, BOM/availability, dimensioned sections,
   assembled/exploded views and insertion sequence, worst-case clearance table, ERC/DRC
   reports, and every waived or untested check with reason and risk. Distinguish nominal
   calculations, tolerance checks, and physical measurements. Do not describe the board
   as tested or manufacture-ready on the strength of a render.
