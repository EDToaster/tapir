#!/usr/bin/env bash
# Linux x86-64 minimal host bundle + Cortex-M toolchain, from the official release.
set -euo pipefail
[[ $(uname -s)/$(uname -m) == Linux/x86_64 ]] || { echo "This helper is for Linux x86_64" >&2; exit 2; }
dest=${1:?Usage: setup-sdk.sh /absolute/dedicated/sdk-cache}
mkdir -p "$dest"; cd "$dest"
base=zephyr-sdk-0.16.8_linux-x86_64_minimal.tar.xz
arm=toolchain_linux-x86_64_arm-zephyr-eabi.tar.xz
for file in "$base" "$arm"; do
    if [[ ! -f "$file" ]]; then
        if command -v gh >/dev/null; then
            gh release download -R zephyrproject-rtos/sdk-ng v0.16.8 -p "$file"
        else
            curl --fail --location --output "$file" "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.8/$file"
        fi
    fi
done
printf '%s  %s\n' c323afcd22149ef0f217759a478bf8b3a42d2e36c89b653a0b875db88d7677e4 "$base" \
    2f77a13e419e9b3bf113cb54eab6060869719477a459453434ec2f4ad536611d "$arm" | sha256sum -c -
tar xf "$base"; tar xf "$arm" -C zephyr-sdk-0.16.8
printf 'Set ZEPHYR_SDK_INSTALL_DIR=%s/zephyr-sdk-0.16.8\n' "$PWD"
