The left and right application images were each linked in two local west workspaces. A fresh checkout of the pinned dependencies and a second build produced byte-for-byte identical UF2s for both hands. This did not flash hardware, dispatch a hosted workflow, or test a physical radio or charging circuit.

| Hand | UF2 bytes / blocks | Application flash | Static RAM | UF2 SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Left, split peripheral | 343040 / 670 | 171412 B | 32436 B | `18d1226dc23082fd1310f035b61fa516c2bebe95eaa03eaeeba47b0bdbf62c90` |
| Right, split central | 511488 / 999 | 255632 B | 74186 B | `c9359935a6b20a584d0e639a143fb11e18457963dd79a0dde0aa805a7f798a82` |

Both start at application address 0x27000 and target nRF52840 UF2 family 0xADA52840. Neither contains NVS/settings, the bootloader or a SoftDevice update. RAM is from the linker, not a high-water measurement.

## Local commands

With the pinned Python environment active, the fresh build used the following shell commands, starting from `product/firmware`:

```sh
export ZEPHYR_SDK_INSTALL_DIR=/tmp/tapir-fw/zephyr-sdk-0.16.8
export TAPIR_FW_WORK=/tmp/tapir-fw-rebuild  # previously empty
bash tools/build.sh
for h in left right; do
  cmp "$TAPIR_FW_WORK/build-$h/zephyr/zmk.uf2" "build-evidence/$h/zmk.uf2"
  cmp "$TAPIR_FW_WORK/build-$h/zephyr/zephyr.dts" "build-evidence/$h/zephyr.dts"
done
python3 tools/check.py
(cd build-evidence && sha256sum -c SHA256SUMS)
```

The host-side test used the official ZMK runner `ZEPHYR_TOOLCHAIN_VARIANT=host ZMK_BUILD_DIR=... ./run-test.sh .../tests/pointer`, with the Tapir transform, keymap and input listener. The [observed events](native-pointer-events.txt) match the checked-in expectation. The offline verifier checks the original reference keymap, effective hold triggers, the two ECAD matrices against the firmware transform/glyphs, resolved GPIO/roles, and every UF2 block; it is not an electrical simulation.

The production build emitted warnings about the pinned app's deprecated `config/boards` convention, inherited DTS `label` fields, NRF reboot GPREGRET and shared peripheral addresses. The board's USB default is requested but resolves off on the left split peripheral as intended. Controller priorities are altered by the community PS/2 driver on the right. Do not infer latency, attach reliability, runtime or safety compliance from the linker or native test. The explicit [bench acceptance checklist](../BENCH.md) is still open.

## Simulated BLE host and split links

Built the upstream `zmk/app/tests/ble/central` host and Tapir test roles with `west build -b nrf52_bsim`. The right was built with `-DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=y`; the left uses `tests/split-ble/peripheral.overlay`. Sensor and switch waveforms are injected, but the two firmware instances and the host communicate via the simulator's BLE controller and GATT paths. All three programs ran for 26 simulated seconds. The following was run locally twice using the compiled simulator executables and yielded the same report sequence:

```sh
w=/tmp/tapir-fw
bash tests/split-ble/run.sh "$w/ws/tools/bsim" "$w/sim-l" "$w/sim-r" "$w/sim-host" "$w/sim-record"
python3 tests/split-ble/verify-host.py build-evidence/split-ble-host.txt
```

The [host log](split-ble-host.txt) shows pairing, mouse-report subscription and 13 notifications. In the [decoded trace](split-ble-decoded.txt), tuples are button mask, relative X, relative Y, vertical wheel and horizontal wheel. Both drags carry a held button while moving, whereas scrolling has zero cursor motion and no button bit; both bits and the layer return to neutral. The fresh production build did not depend on BabbleSim. This idealized, single-session run does not test physical radio reliability, the XIAO hardware, PS/2 electrical protocol, or sleep/wake.
