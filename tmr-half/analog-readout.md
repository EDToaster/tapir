# Analog readout

How 28 sensor outputs get into the nRF52840's ADC, and why. This backs decision D7 and the readout parts of D9 and D10 in [design-decisions.md](design-decisions.md). Values are tagged **drawing**, **measured** or **allowance** as in the rest of the project. Calculations are nominal unless stated.

## The problem in one paragraph

Each TMR2617S puts out a voltage that tracks how far its key is pressed. The ADC converts a voltage into a number, but only on its analog input pins. The nice!nano v2 has three free ones: P0.02 (AIN0), P0.29 (AIN5) and P0.31 (AIN7). An analog multiplexer is a chip of electronic switches. Four digital "select" pins choose which one of its 16 inputs is connected to its single output. Step the select pins through 0–15, read the ADC at each step, and one ADC pin reads 16 keys. Two multiplexers on two ADC pins cover 32 keys. If the muxes share the select pins, their outputs change together. The nRF52840 SAADC samples the two channels in sequence within each address step ([Nordic SAADC, Scan mode](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/saadc.html?contentId=bm_q_Ag2gilDS1VvOSYtDA), **drawing**).

## Architectures considered

| Option | Fits nice!nano? | Verdict |
| --- | --- | --- |
| Two 16:1 muxes, shared select lines, two ADC pins | Yes: 4 select GPIOs, 2 analog pins, 4 spare channels | **Proposed.** Matches the [zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect) driver. It requests one multichannel ADC read at each shared mux address. |
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

For 16 addresses and two sequential samples per address, allow 3 µs acquisition and about 2 µs conversion per sample. Nordic lists 3 µs acquisition for source resistance up to 10 kΩ ([SAADC, Acquisition time and Scan mode](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/saadc.html?contentId=bm_q_Ag2gilDS1VvOSYtDA), **drawing**). A 2 µs address wait gives 16 × (2 + 2 × 5) = 192 µs. A 20 µs wait gives 16 × (20 + 2 × 5) = 480 µs. Both figures are estimated hardware lower bounds for complete scans. They exclude GPIO, driver and scheduling overhead, transport, processing, repeat reads and averaging. Using 10 µs acquisition, as in the coupon's starting ZMK sketch, makes the second estimate 704 µs for the same 16-address scan. Do not infer a measured 1 kHz rate from these figures.

The ZMK driver uses `k_usleep` for `address-to-read-delay`. The elapsed delay depends on kernel timing and can be longer than requested. Use the bare-metal build's busy-wait or hardware timer for T3. Measure the delay from the last address change to ADC acquisition and record the full scan time with the intended averaging.

| Noise budget item | Value | What it means |
| --- | --- | --- |
| TMR2617S output noise | Up to 10 mV peak-to-peak at 3.3 V over 5 kHz ([MDT datasheet, p. 4](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf), **drawing**) | About 12 counts at 12 bits over a nominal 3.3 V ADC span, or 1.5% of a 0.66 V signal (**estimates**). The coupon's bypass, ADC and rail normalization may change the observed noise. |

If the smallest trigger step is near the observed noise, try averaging and use T2 to find the smallest useful window. Averaging reduces random noise when samples are sufficiently independent. It cannot be sized from the peak-to-peak datasheet value alone. Taking extra samples costs ADC time, and averaging across scans adds response delay. Record peak-to-peak noise, RMS noise and scan time with the proposed filter. Check rapid-trigger thresholds against measured counts per millimetre in the part of travel they use.

## Proposed part

**TI CD74HC4067SM96**, 16:1, SSOP-24, 2–6 V supply, signals from GND to VCC (**drawing**, [TI datasheet](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)). LCSC C98457 listed 1,257 in stock from $0.3039 on 2026-11-27 ([LCSC](https://www.lcsc.com/product-detail/C98457.html)). Others have built Gateron LP magnetic Jade boards on it ([r/AskElectronics](https://www.reddit.com/r/AskElectronics/comments/1rwy1st/ortholinear_hall_effect_keyboard/)).

Second sources with the same function but **different footprints**, so pick one footprint before layout:

- Nexperia 74HC4067PW,118, TSSOP-24 ([JLCPCB C179326](https://jlcpcb.com/partdetail/74HC4067PW,118/C179326), Extended part)
- TI CD74HC4067M96, SOIC-24, larger and easier to hand-solder ([JLCPCB C496123](https://jlcpcb.com/partdetail/TexasInstruments-CD74HC4067M96/C496123), Extended part)

Neither datasheet specifies RON at 3.3 V. Nexperia warns that on-resistance becomes very nonlinear near 2 V; 3.3 V is well clear of that. This is the main reason the ADG706 stays as a fallback.

## Circuit rules for the schematic

- Keep the muxes on the module's 3.3 V supply while pulsing a sensor rail. Use a 100 nF bypass capacitor at each mux supply pin (**drawing**, coupon schematic).
- Before switching any sensor rail or the module's 3.3 V supply off, stop ADC sampling and drive S0–S3 low. Keep sampling stopped while the relevant supply is off. Restore power before driving an address and use the measured wake delay before reading a key. Keep any other driven signals to an unpowered mux low or inactive. The [TI mux datasheet](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf) includes input and output clamp-current limits; normal operation should avoid forward-biasing those clamps.
- Tie unused inputs to GND after reserving the rail-monitor channel. The coupon puts grounded inputs between live channels. Use the final channel map for T3. For the full board, choose channel order and ground placement to fit routing and the measured settling budget.
- Connect each mux output straight to its ADC pin. Leave an unpopulated series-resistor and capacitor footprint at the ADC input for noise experiments (the Artery reference design in the GRIDDLE LX table uses one).
- Add an optional footprint at each sensor output for the datasheet's CL (0.1 nF; 10 nF max load) ([TMR2617S-AAC datasheet](https://www.dowaytech.com/en/res/202408/21/dd53d68876041b0f.pdf)). Populate it only if the test board shows that sensor recovery limits settling.
## Supply and reference

With gain 1/4 and reference VDD/4, the ADC full scale follows the nRF52840's own VDD ([Nordic SAADC, Reference](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/saadc.html?contentId=bm_q_Ag2gilDS1VvOSYtDA), **drawing**). The sensor output scales with its own supply. The module regulator, rail FET and shunt can leave those two voltages different. Setting VDD/4 alone leaves that difference in the reading.

For the coupon, read a key and its own rail's MON channel through the same ADC channel with the rail stable. Use readings close together in time. Subtract that mux's ground reading from both. Then compute `Vout / Vsensor ≈ (key − ground) / (2 × (MON − ground))`. The factor of two is for the coupon's equal 10 kΩ divider resistors (**drawing**). Check for MON near zero before dividing. For a different divider, use its actual division ratio. T7 compares raw and corrected readings on USB and battery. Divider tolerance, quantization and changes between samples can leave a residual error.

- The genuine nice!nano v2 enables external VCC with P0.13 high. Driving it low disables that output ([ZMK v2 board overlay](https://github.com/zmkfirmware/zmk/blob/main/app/boards/nicekeyboards/nice_nano/nice_nano_nrf52840_zmk_2_0_0.overlay), **drawing**).
- The [documented SuperMini version](https://wiki.icbbuy.com/doku.php?id=developmentboard:nrf52840) also disables its VCC output when P0.13 is low. Clone regulators and wiring vary. Verify P0.13 and VCC on the actual module before soldering. If probing the two rails to compare them, identify VDD from the module's schematic first.
- Leave external VCC enabled in normal coupon tests. Use Q1 and Q2 for sensor rail control. Coupon rail B is on P1.04, which Nordic labels standard drive, low-frequency I/O only ([Pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/pin.html), **drawing**). Keep switching slow; use unrestricted P0 pins for the proposed full-board rail controls.
