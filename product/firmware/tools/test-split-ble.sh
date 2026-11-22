#!/usr/bin/env bash
# Optional three-node HID integration scenario. No physical radio, USB or PS/2.
set -euo pipefail
FW=$(cd "$(dirname "$0")/.." && pwd)
work=${TAPIR_BLE_WORK:?Set TAPIR_BLE_WORK to a dedicated, initially empty directory}
mkdir -p "$work"
work=$(cd "$work" && pwd)
case "$work/" in "$FW/"*) echo "Keep simulation outside source" >&2; exit 2;; esac
cd "$work"
if [[ ! -f .tapir-ble-sim ]]; then
    [[ -z "$(ls -A)" ]] || { echo "Refusing another workspace" >&2; exit 2; }
    touch .tapir-ble-sim
fi
mkdir -p config
# Keep extra modules out of the production dependency graph; use the exact
# revisions in the same pinned Zephyr manifest for the simulated nRF hardware.
python - "$FW/config/west.yml" <<'PY'
import sys, yaml
from pathlib import Path
m = yaml.safe_load(Path(sys.argv[1]).read_text())
z = next(p for p in m['manifest']['projects'] if p['name'] == 'zephyr')
z['import']['name-allowlist'] += [
    'bsim', 'babblesim_base', 'babblesim_ext_2G4_libPhyComv1',
    'babblesim_ext_2G4_phy_v1', 'babblesim_ext_2G4_channel_NtNcable',
    'babblesim_ext_2G4_modem_magic', 'nrf_hw_models',
]
Path('config/west.yml').write_text(yaml.safe_dump(m, sort_keys=False))
PY
if [[ ! -d .west ]]; then west init -l config; fi
west config --local manifest.group-filter +babblesim
west update --narrow --fetch=smart -o=--depth=1
for patch_spec in "zmk no-sleep-while-held.patch" "kb_zmk_ps2_mouse_trackpoint_driver ps2-open-drain.patch"; do
    read -r repo p <<<"$patch_spec"
    if ! git -C "$repo" apply --reverse --check "$FW/patches/$p" 2>/dev/null; then
        git -C "$repo" apply --check "$FW/patches/$p"
        git -C "$repo" apply "$FW/patches/$p"
    fi
done
export ZEPHYR_BASE="$work/zephyr" ZEPHYR_TOOLCHAIN_VARIANT=host
export BSIM_OUT_PATH="$work/tools/bsim" BSIM_COMPONENTS_PATH="$work/tools/bsim/components"
export BSIM_BUILD_FAIL_ASAP=1 CMAKE_BUILD_PARALLEL_LEVEL=${CMAKE_BUILD_PARALLEL_LEVEL:-4}
make -C "$BSIM_OUT_PATH" -j"$CMAKE_BUILD_PARALLEL_LEVEL" ext_2G4_phy_v1 ext_2G4_channel_NtNcable ext_2G4_modem_magic
testdir="$FW/tests/split-ble"
args=("-DZephyr_DIR=$ZEPHYR_BASE/share/zephyr-package/cmake")
west build -d host -b nrf52_bsim zmk/app/tests/ble/central -- "${args[@]}"
west build -d right -b nrf52_bsim zmk/app -- "${args[@]}" "-DZMK_CONFIG=$testdir" -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=y
west build -d left -b nrf52_bsim zmk/app -- "${args[@]}" "-DZMK_CONFIG=$testdir" "-DEXTRA_DTC_OVERLAY_FILE=$testdir/peripheral.overlay"
bash "$testdir/run.sh" "$BSIM_OUT_PATH" "$work/left" "$work/right" "$work/host" "$work/observed"
