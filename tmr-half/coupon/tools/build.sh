#!/bin/sh
# Regenerate the coupon from tools/design.py and run every gate.
#   tools/build.sh           rebuild using the checked-in routing (routing/tmr-coupon.ses)
#   tools/build.sh reroute   also rerun FreeRouting first (needs FREEROUTING_JAR) and accept its result
# Needs docker (kicad/kicad:10.0.8), python3, rsvg-convert, gerbonara 1.6.3 and Shapely 2 for readback
# (CAM_PYTHON, default python3). Stops at the first failing step.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd); cd "$here"
k=tools/kicad.sh
mkdir -p build reports docs routing

python3 tools/design.py
python3 tools/bom.py
$k python3 tools/footprints.py
$k python3 tools/project.py
$k python3 tools/schematic.py

$k kicad-cli sch erc --severity-all --exit-code-violations --format report -o reports/erc.rpt tmr-coupon.kicad_sch
$k kicad-cli sch export netlist --format kicadxml -o build/netlist.xml tmr-coupon.kicad_sch
python3 tools/check_schematic.py build/netlist.xml

python3 tools/silk_pattern.py
$k python3 tools/place_board.py
if [ "${1:-}" = reroute ]; then
  $k python3 tools/route_board.py dsn --route-ground --out2-guide
  tools/freerouting.sh
  cp build/route/tmr-coupon.ses routing/tmr-coupon.ses
fi
$k python3 tools/route_board.py ses

$k kicad-cli pcb drc --schematic-parity --all-track-errors --severity-all --exit-code-violations \
  --format json -o reports/drc.json tmr-coupon.kicad_pcb

$k python3 tools/check_silk.py
$k python3 tools/check_mechanical.py
$k python3 tools/check_analog.py
$k python3 tools/export_fab.py
$k python3 tools/check_cpl.py
"${CAM_PYTHON:-python3}" tools/check_cam.py
"${CAM_PYTHON:-python3}" tools/check_gerber_silk.py

# Publish stable reports: these fields record the machine clock, not a gate result.
sed -i -E '1s/\([^,]*, Encoding/(Encoding/' reports/erc.rpt
sed -i -E '/^[[:space:]]+"date": /d' reports/drc.json

$k kicad-cli sch export svg --exclude-drawing-sheet --no-background-color -o build/sch tmr-coupon.kicad_sch >/dev/null
rsvg-convert -b white -w 3000 build/sch/tmr-coupon.svg -o docs/schematic.png
# Plot orthographic layer views; the 3D renderer can vary across identical runs.
for side in top bottom; do
  case "$side" in
    top) layer=F; mirror= ;;
    bottom) layer=B; mirror=--mirror ;;
  esac
  $k kicad-cli pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet \
    --layers "$layer.Cu,$layer.Silkscreen,Edge.Cuts" $mirror \
    -o build/board-$side.svg tmr-coupon.kicad_pcb >/dev/null
  rsvg-convert -b white -w 2200 build/board-$side.svg -o docs/board-$side.png
done
echo "build ok"
