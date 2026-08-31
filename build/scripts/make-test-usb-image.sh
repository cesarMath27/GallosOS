#!/usr/bin/env bash
# make-test-usb-image.sh — Builds a synthetic, rootless raw disk image
# reproducing the 2-partition GALLOS_BOOT (FAT32) + event-data (ext4)
# layout (docs/ARCHITECTURE.md §4 item 5), for QEMU-only boot testing of
# ROADMAP.md Phase 1's .gsm module mounting, GALLOS_BOOT config exposure,
# and event-data label-mount. NOT a gallos-flash-provisioned drive image —
# purely a test fixture for build/scripts/test-iso-qemu.sh --usb-image.
#
# Built without root/sudo: partitions are assembled as separate files with
# mkfs.vfat/mkfs.ext4 (both work directly against a plain file, no loop
# device needed) and mtools (mcopy/mmd, rootless FAT access), then dd'd
# into the final image at fixed, 1MiB-aligned offsets — avoiding the
# losetup/kpartx step that would otherwise require root to expose
# individual partitions of a raw disk image as block devices.
#
# Usage: bash build/scripts/make-test-usb-image.sh /path/to/output.img
set -euo pipefail

OUT="${1:?Usage: $0 /path/to/output.img}"

BOOT_START_MIB=1
BOOT_SIZE_MIB=64
DATA_START_MIB=$((BOOT_START_MIB + BOOT_SIZE_MIB))
DATA_SIZE_MIB=32
TOTAL_MIB=$((DATA_START_MIB + DATA_SIZE_MIB + 1))

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Building GALLOS_BOOT (FAT32, ${BOOT_SIZE_MIB} MiB) partition content..."
BOOT_IMG="$WORKDIR/boot.img"
truncate -s "${BOOT_SIZE_MIB}M" "$BOOT_IMG"
mkfs.vfat -F 32 -n GALLOS_BOOT "$BOOT_IMG" >/dev/null

# A dummy .gsm module: get_backing_device() (patched by
# casper-gsm-overlay.sh) treats *.gsm as a SquashFS image regardless of
# extension, so a tiny empty-directory squashfs is a valid, minimal test
# module — content doesn't matter for verifying the mount mechanism.
EMPTY_DIR="$WORKDIR/empty"
mkdir -p "$EMPTY_DIR"
mksquashfs "$EMPTY_DIR" "$WORKDIR/test.gsm" -noappend -comp zstd >/dev/null

cat > "$WORKDIR/gallos.toml" <<'EOF'
# Synthetic fixture for build/scripts/test-iso-qemu.sh --usb-image.
mode = "Default"

[global]
event_name = "GallosOS QEMU Test Fixture"
EOF

mmd -i "$BOOT_IMG" ::/gallos
mmd -i "$BOOT_IMG" ::/gallos/modules
mmd -i "$BOOT_IMG" ::/gallos/config
mcopy -i "$BOOT_IMG" "$WORKDIR/test.gsm" ::/gallos/modules/test.gsm
mcopy -i "$BOOT_IMG" "$WORKDIR/gallos.toml" ::/gallos/config/gallos.toml

echo "Building event-data (ext4, ${DATA_SIZE_MIB} MiB) partition content..."
DATA_IMG="$WORKDIR/eventdata.img"
truncate -s "${DATA_SIZE_MIB}M" "$DATA_IMG"
mkfs.ext4 -q -F -L event-data "$DATA_IMG"

echo "Assembling ${TOTAL_MIB} MiB disk image -> $OUT..."
truncate -s "${TOTAL_MIB}M" "$OUT"
parted -s "$OUT" mklabel msdos
parted -s "$OUT" mkpart primary fat32 "${BOOT_START_MIB}MiB" "$((DATA_START_MIB))MiB"
parted -s "$OUT" mkpart primary ext4 "${DATA_START_MIB}MiB" "$((DATA_START_MIB + DATA_SIZE_MIB))MiB"
dd if="$BOOT_IMG" of="$OUT" bs=1M seek="$BOOT_START_MIB" conv=notrunc status=none
dd if="$DATA_IMG" of="$OUT" bs=1M seek="$DATA_START_MIB" conv=notrunc status=none

echo "Test USB image ready: $OUT"
echo "Use with: bash scripts/test-iso-qemu.sh --usb-image $OUT"
