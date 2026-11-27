Tapir Rev A has two distinct application images. The **right is the BLE/USB host-facing central** and runs the pointing stick; the **left is the BLE split peripheral** and sends the 21 typing and three mouse-switch positions. There is no TRRS interconnect, I²C proxy, display shield, or third dongle. These are compiled prototype candidates, not factory-tested releases.

| Physical hand | File | Flash / 788 KiB | RAM / 256 KiB |
| --- | --- | ---: | ---: |
| Left: 24 populated switches | [Left UF2](build-evidence/left/zmk.uf2) | 171,412 B | 32,436 B |
| Right: 21 switches and PS/2 | [Right UF2](build-evidence/right/zmk.uf2) | 255,632 B | 74,186 B |

Each image has its own [left](build-evidence/left/) or [right](build-evidence/right/) resolved Kconfig and devicetree. [Verification](#verification) explains what the binaries demonstrate and what they do not. Preserve the accompanying [third-party notices](licenses/README.md).

## Electrical and scan contract

Both controllers must be the **non-Sense XIAO nRF52840 Plus**, Seeed 102010672. The [pinned ZMK v0.3.0 board](https://github.com/zmkfirmware/zmk/blob/edf5c0814fd3ea202e43aad2d68fd32e882a518c/app/boards/seeeduino_xiao_ble.overlay) plus its [pinned Zephyr board definition](https://github.com/zmkfirmware/zephyr/blob/dacab4875df72109b96cc8977547a0dc04875bcd/boards/arm/seeeduino_xiao_ble/seeeduino_xiao_ble.dts) is named `seeeduino_xiao_ble`, **not** a distinct Plus target. It supplies the nRF52840, XIAO D0–D10, battery ADC and UF2 application partition. The shield directly names the additional SoC pins on the Plus; do not install the original XIAO BLE, a Sense board, or another XIAO merely because UF2 compiles. Verify the exact board revision, bootloader partition, pad continuity and exposure against [Seeed's Plus pin map](https://wiki.seeedstudio.com/XIAO_BLE/) and [Rev 1.1 PCB archive](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip).

| Scope | Signal | XIAO pad and nRF GPIO | Contract |
| --- | --- | --- | --- |
| Both | R0…R3 | D0 P0.02, D1 P0.03, D2 P0.28, D3 P0.29 | Active-high pulled-down scan inputs; matrix wakes its own half. |
| Both | C0…C5 | D4 P0.04, D5 P0.05, D6 P1.11, D7 P1.12, D8 P1.13, D9 P1.14 | Active-high driven columns; diode cathode faces row. Number outermost → innermost on both hands. |
| Right | TP_DATA | D10 P1.15 | PS/2 directly sampled/written against real clock; GPIO is input or output open-drain. |
| Right | TP_CLK | D11 P0.15 | Plus pad; falling-edge GPIO interrupt, not UART baud guessing. |
| Right | TP_RST | D12 P0.19 | Plus pad; active high; inactive low before sensor power and shutdown. |
| Right | TP_EN | D13 P1.01 | Plus pad; active-high TPS22918 enable with external pulldown. CLK/DATA pullups belong to switched 3.3 V, not always-on. |
| Both | Charger rate select | On-module P0.13, **not D13** | Input, no pull. Never drive low. Not an expansion pad allocation. |

R3C3, C4 and C5 select the outer, middle and inner thumb on each half. R3C0, C1 and C2 on the left are left-click, momentary scroll, and right-click. The three corresponding right slots are empty. The right scanner reverses its column array and adds six; no firmware swap of left/right roles changes logical position numbering. P0.31 is reserved for the battery ADC, P0.14 for its divider gate and NFC pins are unused. The external flash and unused serial/I²C/SPI nodes are disabled; their standby current is not assumed zero.

The [Sprintek SK8707-01 drawing and electrical table, pp. 3–5](https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=3) distinguish host castellations from the sensor cable: on the selected -004 driver, 1 GND, 2 DATA, 3 CLK, 4 RESET, 5 3.3 V, and 6/7/8 button inputs. Leave the latter out of the host HID path. Ordinary Zephyr/ZMK at this revision does not provide this nRF GPIO PS/2 mouse transport. The **pinned community driver**, not a claimed upstream ZMK feature, is [badjeff's fork of infused-kim's PS/2 module](https://github.com/badjeff/kb_zmk_ps2_mouse_trackpoint_driver/tree/5ff0b24863ab74390adcc447b0575fcd78442514); its source components are mirrored in [vendor](vendor/) and [its explicit adaptation](patches/ps2-open-drain.patch) is applied before build. On TX, high means release; on RX, no host pull is enabled. The patch initializes the receive work/FIFO before enabling interrupts, initializes the packet timer before starting callback reporting, clears stale pre-reset BAT/ID bytes, and gives the callback workqueue a larger stack.

## Keymap and pointer

[EDToaster's actual Corne keymap at 4fc3285](https://github.com/EDToaster/edtoaster-zmk-keymaps/blob/4fc3285c8436de332c8218bcda881c09e30f472e/config/corne.keymap) is the reference, not the Lily58 map or a generic QWERTY remap. Base, Lower, and Raise retain all **42 original bindings per layer**, including the six thumb bindings, Bluetooth profiles and media keys. F and J still tap the letter or hold left GUI, with balanced flavor, 280 ms tapping term, 175 ms quick tap, 150 ms prior-idle and hold-trigger-on-release. The only hold-trigger edit removes previously out-of-range positions (42–57) from the inherited lists so new mouse positions cannot silently become opposite-hand typing triggers. All existing effective indices are unchanged.

| Position | Gesture | Result |
| --- | --- | --- |
| 42, physical L | Press/hold then move right stick | Left-button down; drag continues until explicit release or split disconnect cleanup. |
| 43, physical Scroll | Hold while moving right stick | Temporary layer 3 maps X→horizontal wheel, Y→vertical wheel, divided by 12 with remainder. Release returns to relative pointer movement. It is not a middle click. |
| 44, physical R | Press/hold then release | Right-button down/up. |

Lower/Raise pass the three controls through. Scroll is transparent for every typing position; it consumes one formerly reserved Studio layer. The physical layout for Studio is a key-selection diagram, not fabrication geometry. The PS/2 head cannot generate mouse clicks in firmware; do not infer that Suppressed HID clicking electrically disables the Sprintek Z-Tap or earns the lower idle-current number. Axis signs assume the chosen sensor orientation: validate stock assembled mounting in both axes before fixing the final transform.

The [reference manifest](https://github.com/EDToaster/edtoaster-zmk-keymaps/blob/4fc3285c8436de332c8218bcda881c09e30f472e/config/west.yml) selects ZMK v0.3.0. Tapir locks its commit, Zephyr, and the pointer module; transitive dependency SHAs are listed in [dependencies.tsv](build-evidence/dependencies.tsv). The source user's toast-view module is intentionally omitted: neither Tapir nor the original Corne entry uses this display. Debounce 1/10 ms, +8 dBm radio TX, battery proxy/fetch and Studio locking disabled are preserved (with USB Studio on the right). Treat an unlocked Studio session as a trusted remapping interface. A keymap already saved in Studio can override compiled defaults; back up custom changes before resetting a test unit.

## Power, wake and flashing

The [right-side rail owner](src/pointer_rail.c) powers the driver after the PS/2 GPIO bus exists; a delayed initialization pulses active-high RESET for 600 ms, then waits for PS/2 self-test/ID and enables reporting. These are driver assumptions, not measured timings. A disconnected pointer does not intentionally block keyboard boot. Ordinary connected idle leaves the rail on so the stick can wake the cursor. At 15 min without input on battery, ZMK enters system-off: mask the clock edge, detach DATA/CLK, hold RESET low, then turn off TP_EN. Wake via a matrix switch on that half is a cold initialization, not just a rail toggle. A failed suspend that already switched the rail off forces a cold restart. A [held-position sleep guard](patches/no-sleep-while-held.patch) keeps the peripheral awake while a mouse switch is physically held, even if only the opposite half's stick is moving. On actual split loss ZMK's [central release path](https://github.com/zmkfirmware/zmk/blob/edf5c0814fd3ea202e43aad2d68fd32e882a518c/app/src/split/bluetooth/central.c) emits releases for formerly down positions; 32 queue entries exceed the 24 left contacts. Abrupt RF failure is not instantaneous: release latency depends on link supervision and queue servicing.

**Neither a powered-down pointing stick nor a sleeping central listens for a left key over BLE.** After both halves sleep, press a right typing key to wake the central and a left key if that half is asleep. Do not promise a wake key is delivered; before typing or pointing, wait for split and host reconnection. The cell disconnect isolates the battery, not USB logic power: power down/unplug USB before servicing, and do not assume the switch stops the MCU while USB is attached.

P0.13 high impedance is the application's charger selection for the [Adafruit 1570 protected pack](https://www.adafruit.com/product/1570). Validate about 50 mA, not the high-current path, through real bootloader, double-reset DFU, firmware boot and sleep; an application cannot control bootloader GPIO or prove a module's resistor population. Do not charge a pack for the first bring-up. Follow the independent [hardware validation](../validation/) and [sourcing record](../sourcing/) before connecting it.

As a source cross-check, the [upstream Adafruit XIAO bootloader board definition inspected](https://github.com/adafruit/Adafruit_nRF52_Bootloader/blob/0ee83433a6b8ec23341629d2407cbf0fc62335f3/src/boards/xiao_nrf52840_ble/board.h) assigns P0.26/P0.06 to LEDs and P0.18/P0.03 to buttons, not P0.13. Its teardown returns GPIOs to reset defaults. This does not identify or attest the bootloader or prior firmware present on any delivered Plus board: record INFO_UF2, do first flash battery-disconnected, and qualify each board/loader revision using the charge-current gate.

For USB-only prototype flashing, **remove/disconnect the batteries**, check voltages, and confirm host board ID and bootloader layout before copying anything. Connect one half using a USB data cable, rapidly double-press its reset button to enter the UF2 bootloader ([Seeed reset instructions](https://wiki.seeedstudio.com/XIAO_BLE/)). Inspect its boot volume/INFO_UF2 record; stop on a target or partition mismatch. Copy **only** its matching hand's `zmk.uf2` to that volume, wait for its automatic reboot, then repeat for the other hand. Do not mass erase, overwrite the bootloader, or flash a settings-reset image casually. Power both halves together for initial split pairing; the host pairs to the **right** named Tapir. If replacing an existing pairing, follow the [ZMK split troubleshooting guide](https://zmk.dev/docs/troubleshooting/connection-issues) and preserve existing bonds unless intentionally clearing them.

## Rebuild without hosted services

The following is the local Linux x86-64 path. It does not send an image to a device, dispatch a workflow, or require writes to a remote repository. Prerequisites: Git, a host C compiler and libc headers, bash, tar/xz, SHA-256, devicetree compiler and gperf. On the test host protoc 3.21.12 was also available. Use Python 3.11 and the pinned host tools. From `product/firmware`:

```sh
# Example once on Debian/Ubuntu: install build-essential device-tree-compiler gperf protobuf-compiler.
uv python install 3.11.17
uv venv --python 3.11.17 "$HOME/.cache/tapir-py311"
uv pip sync --python "$HOME/.cache/tapir-py311/bin/python" requirements-lock.txt
. "$HOME/.cache/tapir-py311/bin/activate"
bash tools/setup-sdk.sh "$HOME/.cache/tapir-sdk"
export ZEPHYR_SDK_INSTALL_DIR="$HOME/.cache/tapir-sdk/zephyr-sdk-0.16.8"
export TAPIR_FW_WORK="$HOME/.cache/tapir-west"  # empty on first use; dedicated afterwards
bash tools/build.sh
```

The [official SDK 0.16.8 release](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v0.16.8) supplies ARM GCC 12.2.0; the helper verifies the two official archive SHA-256 values before extracting them. The build script uses west 1.4.0, CMake 3.31.6 and Ninja 1.13.2, downloads only the resolved graph, applies both patches idempotently and passes the Tapir Zephyr module path explicitly. Plain stock ZMK build commands without its patches/module are **not** a valid substitute. To produce only the two application binaries after bootstrap:

```sh
FW="$(pwd -P)"                       # starting in product/firmware
cd "$TAPIR_FW_WORK"
west build -d build-left -b seeeduino_xiao_ble zmk/app -- \
  "-DZMK_CONFIG=$FW/config" "-DZMK_EXTRA_MODULES=$FW" -DSHIELD=tapir_left
west build -d build-right -b seeeduino_xiao_ble zmk/app -- \
  "-DZMK_CONFIG=$FW/config" "-DZMK_EXTRA_MODULES=$FW" -DSHIELD=tapir_right -DSNIPPET=studio-rpc-usb-uart
```

## Verification

The [build record](build-evidence/validation.md) gives the two production image digests, commands, and independent compile comparison. Both UF2s were byte-identical across the two workspaces.

Run `python3 tools/check.py` from this directory with Python 3.10+ to cross-check the bundled files offline. It checks a SHA-pinned original keymap, 126 binding identities, both effective home-row trigger sets, 45 unique ECAD switch/legend positions through the shared transform, resolved scan and pointer pins/roles, plus each UF2 block's target, count, order, contiguity and application-only address range. Use `--workspace "$TAPIR_FW_WORK"` to run against your own binaries. From `build-evidence`, use `sha256sum -c SHA256SUMS` to check the bundle.

The [native pointer scenario](tests/pointer/) runs the actual ZMK keymap, matrix transform, input processor and HID button state machine, replacing the scanner and PS/2 events with mocks. Its [observed trace](build-evidence/native-pointer-events.txt) matched all 12 expected transitions. Positive X, inverted cursor Y, left-down during motion, left-up, both scroll axes, return to cursor, right-down during motion, and right-up are all checked. This does not sample an actual PS/2 waveform. See [bench gate](BENCH.md) for the required physical/electrical release tests; no key switch, assembled stick, charge circuit, hand posture, radio link or runtime has been physically validated here. The historic config/boards deprecation and nRF shared unit-address/GPREGRET diagnostics belong to this pinned toolchain; enabling the community GPIO driver also changes controller interrupt priorities. Treat BLE timing and retry behavior as bench items, not closed by a clean link.

The separate [three-node BLE integration test](tests/split-ble/) runs two ZMK instances and an independent Zephyr HID host on the pinned nRF52 BabbleSim radio model. Mock scanner events start on the left, while relative stick motion originates on the right; the inter-half link and right-to-host HOG notifications are exercised rather than bypassed. The host paired, subscribed to mouse reports, and received [13 byte-checked reports](build-evidence/split-ble-decoded.txt), including holds, releases, both wheel axes and returning to cursor movement. The [raw host log](build-evidence/split-ble-host.txt) can be checked offline:

```sh
python3 tests/split-ble/verify-host.py build-evidence/split-ble-host.txt
# To rebuild the modeled radios: use the Python environment above, a 32-bit
# host C toolchain (e.g. Debian gcc-multilib / libc6-dev-i386), GNU make and coreutils.
TAPIR_BLE_WORK="$HOME/.cache/tapir-radio-test" bash tools/test-split-ble.sh
```

The radio model uses an idealized channel and the simulator's default link-layer cipher model; it is not a security, interference, power, mechanical or PS/2 timing test. The installed XIAO bootloader, real host bond persistence, reconnect, held-key timeout and RF-loss bench cases are not covered by this simulation.
