# Working on TMR half

This project is separate from Tapir. Tapir's rules (Choc v1, XIAO nRF52840 Plus, split Corne layout, TrackPoint) do not apply here. The repo-level [AGENTS.md](../AGENTS.md) still applies.

- Record every design choice in [design-decisions.md](design-decisions.md) with a status (Decided, Proposed, Open) and its evidence. Only the owner moves an item to Decided.
- Tag critical values as **drawing**, **measured** (by whom and how) or **allowance**. A value borrowed from another project's measurement stays labeled with that project.
- Use exact manufacturer part numbers, including the TMR2617S sensitivity and offset suffix, with an orderable listing. Flag out-of-stock or single-source parts before designing around them.
- Draw this project's own footprints. Partial-Gauss has no license file, so record its dimensions and credit it, but don't copy its KiCad files. zmk-feature-hall-effect is MIT and can be used as a dependency with attribution.
- Once hardware source exists, follow the same toolchain as Tapir: KiCad 10 with ERC/DRC gates, build123d for the enclosure, and pinned tool versions. Report runtime and polling figures as estimates until they are measured.
