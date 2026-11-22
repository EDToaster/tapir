"""Assert actual HOG notifications received by ZMK's simulated host, not device logs."""
import re
import struct
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text()
if "[MOUSE SUBSCRIBED]" not in raw or "pairing_complete: Pairing complete" not in raw:
    sys.exit("BLE host did not pair and subscribe to the mouse reports")
# (button mask, relative X, relative Y, wheel vertical, wheel horizontal).
expected = [
    (0, 12, 0, 0, 0), (1, 0, 0, 0, 0),
    (1, 0, -12, 0, 0), (1, 12, 0, 0, 0), (1, 12, 0, 0, 0),
    (0, 0, 0, 0, 0), (0, 12, 0, 0, 0),
    (0, 0, 0, -3, 0), (0, 0, 0, 0, 2), (0, 0, -24, 0, 0),
    (2, 0, 0, 0, 0), (2, 12, 0, 0, 0), (0, 0, 0, 0, 0),
]
actual = []
for line in raw.splitlines():
    if "|" not in line:
        continue
    payload = re.search(r"((?:\b[0-9a-fA-F]{2}[ \t]+){9})\|", line)
    if payload:
        data = bytes.fromhex(payload.group(1))
        decoded = struct.unpack("<Bhhhh", data)
        actual.append(decoded)
        print(f"{data.hex(' ')}  ->  {decoded}")
if actual != expected:
    sys.exit(f"Host report mismatch.\nExpected {expected}\nObserved {actual}")
print(f"PASS: {len(actual)} host mouse notifications match right-stick and BLE split-switch activity")
