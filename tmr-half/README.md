# TMR half

A 28-key analog keyboard for the left hand that uses TMR (tunneling magnetoresistance) magnetic sensors under low-profile MX-style magnetic switches. It is half-size to leave more desk room for a mouse. Targets are an adjustable actuation point, rapid trigger, 1 kHz USB polling, and the lowest practical sensor power.

**Status: planning.** No schematic, board or firmware exists yet. Decisions and their evidence are in [design-decisions.md](design-decisions.md).

## Layout

6 columns × 5 rows, 28 keys. The bottom-left and bottom-right positions are empty.

| | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Row 1 | Esc | 1 | 2 | 3 | 4 | 5 |
| Row 2 | Tab | Q | W | E | R | T |
| Row 3 | Shift | A | S | D | F | G |
| Row 4 | Ctrl | Z | X | C | V | B |
| Row 5 | (blank) | Menu | Mod1 | Mod2 | Alt | (blank) |


## Core parts

- Switch: Gateron Low Profile Magnetic Jade Pro
- Sensor: MDT TMR2617S-AAC-0.500-500, placed as in [Partial-Gauss](https://github.com/cr3eperall/partialgauss)
- Controller: nice!nano v2 clone (nRF52840)
- Readout: two 16:1 analog multiplexers
- Firmware: ZMK with [zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect) first

Project rules are in [AGENTS.md](AGENTS.md).
