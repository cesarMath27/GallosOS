#!/usr/bin/env bash
# Runs Stages 1-4 in order inside the gallos-builder container.
# Invoked by ../Makefile; not meant to be run directly on the host.
set -euo pipefail

CONFIG="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="/repo/build/output"
ROOTFS="$OUT_DIR/rootfs"
STAGING="$OUT_DIR/staging"
ISO="$OUT_DIR/gallosOS-custom-amd64.iso"

echo "=== Stage 1: Bootstrap ==="
"$SCRIPT_DIR/01-bootstrap.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 2: Provision ==="
"$SCRIPT_DIR/02-provision.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 3: Optimize ==="
"$SCRIPT_DIR/03-optimize.sh" "$CONFIG" "$ROOTFS"

echo "=== Stage 4a: Squash ==="
"$SCRIPT_DIR/build-squashfs.sh" "$ROOTFS" "$STAGING"

echo "=== Stage 4b: ISO ==="
"$SCRIPT_DIR/build-iso.sh" "$STAGING" "$ISO"

echo "=== Done: $ISO ==="
