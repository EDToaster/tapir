# Analog readout

How 28 sensor outputs get into the nRF52840's ADC, and why. This backs decision D7 and the readout parts of D9 and D10 in [design-decisions.md](design-decisions.md). Values are tagged **drawing**, **measured** or **allowance** as in the rest of the project. Calculations are nominal unless stated.

## The problem in one paragraph

Each TMR2617S puts out a voltage that tracks how far its key is pressed. The ADC converts a voltage into a number, but only on its analog input pins. The nice!nano v2 has three free ones: P0.02 (AIN0), P0.29 (AIN5) and P0.31 (AIN7). An analog multiplexer is a chip of electronic switches. Four digital "select" pins choose which one of its 16 inputs is connected to its single output. Step the select pins through 0–15, read the ADC at each step, and one ADC pin reads 16 keys. Two multiplexers on two ADC pins cover 32 keys. If both share the same select pins, each step reads two keys at once.

## Architectures considered

| Option | Fits nice!nano? | Verdict |
| --- | --- | --- |
| Two 16:1 muxes, shared select lines, two ADC pins | Yes: 4 select GPIOs, 2 analog pins, 4 spare channels | **Proposed.** Matches the `he,kscan-multiplexer` driver in [zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect), which supports several muxes sampled in parallel on shared select lines. |
| Parallel 8:1 muxes, one ADC pin each | No: 28 keys need 4 muxes and 4 analog pins, and only 3 are free | This is the libhmk layout. [GRIDDLE LX](https://erfi.dev/reference/griddle-lx-hall-effect-keyboard/) notes that all four boards in libhmk's tree use it, but it suits MCUs with more ADC pins. |
| External multi-channel SPI or I2C ADC | Yes | Adds cost, power and a driver neither ZMK module has. No accuracy need justifies it: the internal 12-bit SAADC already gives ~820 counts of travel (see the sensor section of the decisions). |
| Precision low-resistance mux (for example ADI [ADG706](https://www.analog.com/en/products/adg706.html), 2.5 Ω, specified from 1.8 V) | Yes | Specified at 3.3 V, but several times the price. Low on-resistance buys nothing here (see below). Keep it as the fallback if the HC part misbehaves at 3.3 V. |

## Why the cheap 74HC4067 is enough

The usual worry with a mux is its switch resistance, called RON: roughly 70–200 Ω for this family. That only matters when current flows through the switch. The nRF52840 ADC draws essentially no steady current. It briefly charges a small sampling capacitor, and Nordic lists 3 µs of acquisition time as enough for sources up to 10 kΩ ([SAADC](https://infocenter.nordicsemi.com/topic/ps_nrf52840/saadc.html), **drawing**). The TMR2617S has a driven op-amp output plus a few hundred ohms of switch, so it sits far below 10 kΩ. RON therefore affects settling time but not the reading.

Settling estimate (**nominal**):

| Quantity | Value | Evidence |
| --- | --- | --- |
| RON | ≤ 300 Ω | **Allowance.** The datasheets give 160–180 Ω max at 4.5 V and none at 3.3 V; [TI](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf), [Nexperia](https://assets.nexperia.com/documents/data-sheet/74HC_HCT4067.pdf) |
| Common-pin capacitance | 45–50 pF | **Drawing** (Nexperia 45 pF, TI 50 pF), plus ~10 pF for the track and ADC as an **allowance** |
| Time constant | ~300 Ω × 60 pF ≈ 18 ns | |
| Settle to 12 bits (~9 time constants) | ~0.2 µs | |
| Select-to-output switching | 60 ns at 4.5 V, 300 ns at 2 V | **Drawing**, TI. 3.3 V falls between. |

The switch itself is settled in well under 1 µs. The unknown is how quickly the sensor's own output stage recovers when it is suddenly connected to the ~50 pF common node, which still holds the previous key's voltage. The TMR2617S lists 50 kHz bandwidth, so recovery could plausibly take several microseconds. Only a measurement on the test board will tell. For comparison, GRIDDLE LX swept settle time from 20 µs down to 2 µs on 3.3 V 8:1 muxes with Hall sensors and found no settling trend, so it ships at 2 µs ([GRIDDLE LX](https://erfi.dev/reference/griddle-lx-hall-effect-keyboard/), **measured** by that project with different sensors).

Even a pessimistic settle fits the budget. One scan is 16 steps × (settle + 2 conversions of about 3 µs acquisition plus roughly 2 µs conversion). At 2 µs settle that is about 190 µs; at 20 µs it is about 480 µs. Both are inside the 1 ms USB report interval.

The ZMK driver waits with a sleep call (`address-to-read-delay`). Its real resolution depends on the kernel tick, so a requested delay of a few microseconds may last tens. Measure the actual scan rate on the test board rather than assuming 1 kHz. The Rust firmware can busy-wait for exact microseconds.

## Proposed part

**TI CD74HC4067SM96**, 16:1, SSOP-24, 2–6 V supply, signals from GND to VCC (**drawing**, [TI datasheet](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)). LCSC C98457 listed 1,257 in stock from $0.3039 on 2026-11-27 ([LCSC](https://www.lcsc.com/product-detail/C98457.html)). Others have built Gateron LP magnetic Jade boards on it ([r/AskElectronics](https://www.reddit.com/r/AskElectronics/comments/1rwy1st/ortholinear_hall_effect_keyboard/)).

Second sources with the same function but **different footprints**, so pick one footprint before layout:

- Nexperia 74HC4067PW,118, TSSOP-24 ([JLCPCB C179326](https://jlcpcb.com/partdetail/74HC4067PW,118/C179326), Extended part)
- TI CD74HC4067M96, SOIC-24, larger and easier to hand-solder ([JLCPCB C496123](https://jlcpcb.com/partdetail/TexasInstruments-CD74HC4067M96/C496123), Extended part)

Neither datasheet specifies RON at 3.3 V. Nexperia warns that on-resistance becomes very nonlinear near 2 V; 3.3 V is well clear of that. This is the main reason the ADG706 stays as a fallback.

## Circuit rules for the schematic

- Power the muxes from the always-on 3.3 V rail, not the switched sensor rail. Add a 100 nF capacitor at each mux supply pin.
- Never let a powered signal reach an unpowered chip. If the muxes are ever switched off, drive the select lines low first. Otherwise current flows through the input protection diodes and partly powers the chip. The TI absolute-maximum ratings allow ±20 mA there; stay far below that.
- Tie the 4 unused channels to ground, as GRIDDLE LX does. They also serve as a known zero for checking settling.
- Connect each mux output straight to its ADC pin. Leave an unpopulated series-resistor and capacitor footprint at the ADC input for noise experiments (the Artery reference design in the GRIDDLE LX table uses one).
- Add an optional footprint at each sensor output for the datasheet's CL (0.1 nF; 10 nF max load) ([TMR2617S-AAC datasheet](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf)). Populate it only if the test board shows that sensor recovery limits settling.
- Order mux channels to follow the physical rows, so neighbouring channels are neighbouring keys. Crosstalk from a key's magnet then shows up the same way in every settle test.

## Supply and reference

The ADC uses VDD/4 as its reference, so it reads a fraction of the nRF52840's own VDD. The TMR2617S output is a fraction of its own supply. If both come from the same rail, supply ripple and drift cancel. If they don't, the cancellation is lost.

- On the genuine nice!nano v2, P0.13 switches power to the VCC pin and setting it high turns VCC off ([nice!nano docs](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)).
- On SuperMini-style clones, the VCC pin comes from a separate ME6217 LDO whose enable is on P0.13, and setting it low turns VCC off ([nrfmicro wiki](https://github.com/joric/nrfmicro/wiki/Alternatives/)). The polarity is reversed, and the nRF's VDD may not be the same rail as the VCC pin.

Before the schematic:

- Identify the clone and measure its VCC pin against the nRF VDD (for example at a decoupling capacitor) with the board on USB.
- Don't use P0.13 for scan-rate power pulsing. Use the project's own sensor switch (D9).
- Route the sensor rail through a high-value divider, with a capacitor at its midpoint, into one spare mux channel. Firmware can then compare the sensor supply against the ADC reference.
