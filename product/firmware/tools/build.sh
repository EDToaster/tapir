#!/usr/bin/env bash
# Local build only; no flashing, uploads or hosted workflows.
set -euo pipefail
FW=$(cd "$(dirname "$0")/.." && pwd)
work=${TAPIR_FW_WORK:?Set TAPIR_FW_WORK to a dedicated build directory outside the source tree}
mkdir -p "$work"
work=$(cd "$work" && pwd)
case "$work/" in "$FW/"*) echo "Workspace must be outside product/firmware" >&2; exit 2;; esac
cd "$work"
if [[ ! -e .tapir-workspace ]]; then
    if [[ -n "$(ls -A)" ]]; then echo "Choose an empty directory; refusing to alter another workspace." >&2; exit 2; fi
    touch .tapir-workspace
fi
mkdir -p config
cp "$FW/config/west.yml" config/west.yml
if [[ ! -d .west ]]; then west init -l config; fi
# Fetch pinned commits themselves, not all branch tips (especially important for shallow clones).
west update --narrow --fetch=smart -o=--depth=1
west zephyr-export
apply_exact() {
    local repo=$1 patch=$2
    if git -C "$repo" apply --reverse --check "$patch" 2>/dev/null; then return; fi
    git -C "$repo" apply --check "$patch"
    git -C "$repo" apply "$patch"
}
apply_exact zmk "$FW/patches/no-sleep-while-held.patch"
apply_exact kb_zmk_ps2_mouse_trackpoint_driver "$FW/patches/ps2-open-drain.patch"
export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
: "${ZEPHYR_SDK_INSTALL_DIR:?Set ZEPHYR_SDK_INSTALL_DIR to the extracted SDK 0.16.8}"
[[ "$(cat "$ZEPHYR_SDK_INSTALL_DIR/sdk_version")" == 0.16.8 ]] || { echo "Expected Zephyr SDK 0.16.8" >&2; exit 2; }
export CMAKE_BUILD_PARALLEL_LEVEL=${CMAKE_BUILD_PARALLEL_LEVEL:-4}
for hand in left right; do
    args=()
    if [[ "$hand" == right ]]; then args+=(-DSNIPPET=studio-rpc-usb-uart); fi
    west build -p auto -d "build-$hand" -b seeeduino_xiao_ble zmk/app -- \
        "-DZMK_CONFIG=$FW/config" "-DZMK_EXTRA_MODULES=$FW" "-DSHIELD=tapir_$hand" "${args[@]}"
done
(
    cd zmk/app
    ZEPHYR_TOOLCHAIN_VARIANT=host ZMK_BUILD_DIR="$work/native" ./run-test.sh "$FW/tests/pointer"
)
python "$FW/tools/check.py" --workspace "$work"
printf 'Images reside in %s/build-{left,right}/zephyr/zmk.uf2\n' "$work"
