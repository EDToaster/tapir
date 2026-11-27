#!/bin/sh
# Plot top and bottom views of a board to PNG for inspection. Usage: tools/view.sh build/tmr-coupon.kicad_pcb build/view
set -eu
here=$(cd "$(dirname "$0")/.." && pwd); cd "$here"
pcb=$1; out=$2; mkdir -p "$out"
tools/kicad.sh kicad-cli pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet --check-zones \
  -l F.Cu,F.Paste,F.SilkS,F.Fab,F.CrtYd,Edge.Cuts,User.Drawings -o "$out/top.svg" "$pcb" >/dev/null
tools/kicad.sh kicad-cli pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet --check-zones --mirror \
  -l B.Cu,B.Paste,B.SilkS,B.Fab,B.CrtYd,Edge.Cuts -o "$out/bottom.svg" "$pcb" >/dev/null
for s in top bottom; do rsvg-convert -b white -w "${WIDTH:-2400}" "$out/$s.svg" -o "$out/$s.png"; done
