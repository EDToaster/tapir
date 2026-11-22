#!/usr/bin/env bash
# Arguments are absolute paths: PHY root, left / right / host builds, log dir.
set -euo pipefail
: "${5:?usage: run.sh BSIM_ROOT LEFT_BUILD RIGHT_BUILD HOST_BUILD LOG_DIRECTORY}"
testdir=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$5"
cd "$1/bin"
id=tapir-$$
pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT
"$3/zephyr/zmk.exe" -d=0 -s=$id >"$5/right.log" 2>&1 & pids+=($!)
"$2/zephyr/zmk.exe" -d=1 -s=$id >"$5/left.log" 2>&1 & pids+=($!)
"$4/zephyr/zephyr.exe" -d=2 -s=$id -subscribe_to_pointer_report >"$5/host.log" 2>&1 & pids+=($!)
timeout 60 ./bs_2G4_phy_v1 -D=3 -s=$id -sim_length=26e6 >"$5/phy.log" 2>&1
for p in "${pids[@]}"; do wait "$p"; done
pids=()
python "$testdir/verify-host.py" "$5/host.log" | tee "$5/decoded.txt"
