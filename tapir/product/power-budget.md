# Right-half battery budget

Seven days is a design target, **not a runtime claim**. The [candidate pack](https://www.adafruit.com/product/1570) is sold as 3.7 V nominal, 100 mAh. Assuming 80% of that nominal energy is usable gives 296 mWh for a week, or **42.29 mWh/day per half**. This is a planning allowance: voltage drops during discharge, real capacity varies, and conversion efficiency and leakage are not known. This calculation does not clear the [charging compatibility hold](sourcing/qualification.md).

The data below use the manufacturer's [SK8707-01 3.3 V typical consumption table, p. 5](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=5), not a measured Tapir. Assume one hour of pointing, seven hours with the sensor connected but idle, and sixteen hours truly rail-off. Ignore switch leakage only for this illustration. The driver draws 2.09 mA active, 1.44 mA idle with Z-Tap enabled or 0.65 mA idle with it disabled. These are **typical**, not maxima. Ignoring click packets in firmware does not disable Z-Tap inside the module.

| Right driver scenario | Driver at 3.3 V, mAh/day | Energy delivered to driver | Battery energy left for everything else at perfect conversion | Energy left at illustrative 90% driver-supply efficiency |
| --- | ---: | ---: | ---: | ---: |
| Z-Tap on while idle | 2.09 + 7 × 1.44 = 12.17 | 40.16 mWh/day | 2.12 mWh/day | **−2.34 mWh/day** |
| Z-Tap off while idle | 2.09 + 7 × 0.65 = 6.64 | 21.91 mWh/day | 20.37 mWh/day | 17.94 mWh/day |

The 90% column is a sensitivity test, not a claim about the XIAO regulator. It uses `42.2857 − (driver mAh × 3.3)/0.90`. The first case does not support a credible seven-day promise: at ideal conversion there is only 2.12 mWh/day for the central MCU, BLE, scanning, any LEDs, rail switching and all losses. In the second scenario there is room in the budget, but the idle mode has to be demonstrated on the actual driver. The left half has no Sprintek; its consumption must be assessed independently.

Measure active, connected-idle, system-off, wake, and split reconnect at each battery input with USB disconnected. Capture a full duty cycle and integrate measured power, including transitions; do not add a module's 3.3 V currents directly to battery currents at a different voltage. If right-idle misses its budget, first verify whether Z-Tap can be disabled on the exact module. Next consider gating the rail sooner with an explicit keyboard wake gesture and validated pointer reinitialization. A bigger battery is a separate enclosure and charging review, not a drop-in firmware fix.
