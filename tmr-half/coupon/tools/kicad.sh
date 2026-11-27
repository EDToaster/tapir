#!/bin/sh
# Run a command inside the pinned KiCad 10.0.8 image with this coupon folder mounted at the same path.
# Usage: tools/kicad.sh python3 tools/place_board.py   |   tools/kicad.sh kicad-cli version
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
exec docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -e KICAD10_3DMODEL_DIR=/usr/share/kicad/3dmodels \
  -v "$here":"$here" -w "$here" kicad/kicad:10.0.8 "$@"
