#!/usr/bin/env bash
# Stage 5b: Squash & Stitch, ISO half (docs/BUILD_SYSTEM.md §3 Stage 5 /
# ROADMAP.md Phase 1 "Hybrid ISO Stitched Image").
#
# Uses grub-mkrescue (which itself shells out to xorriso) to produce a
# hybrid BIOS + UEFI bootable ISO from $STAGING.
#
# NOTE (walking-skeleton scope, see the approved plan): this produces a
# genuinely bootable UEFI image using grub's own unsigned EFI binary, NOT
# yet the Canonical-signed shim/grub-efi-amd64-signed SecureBoot chain that
# ROADMAP.md's "Dual Bootloader Chain" item calls for. Swapping in the
# signed shim as the EFI System Partition's bootx64.efi is the concrete
# next step once this walking skeleton is proven to boot — do not claim
# SecureBoot support until that lands.
#
# NOTE: no md5sum.txt manifest is generated onto the ISO, so the stock
# casper-md5check.service has nothing to verify against and fails at every
# boot (harmless — systemd just logs [FAILED] and continues to
# multi-user.target, verified interactively). This means the produced media
# currently has no integrity self-check for corrupted USB writes/downloads.
# Fix: `find` the staging tree, `md5sum` everything, write md5sum.txt at
# the ISO root here, before the grub-mkrescue call below.
set -euo pipefail

STAGING="$1"
OUT_ISO="$2"
VOLID="GALLOS_BOOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

mkdir -p "$STAGING/boot/grub" "$STAGING/boot/gallos"
if [[ -f "$REPO_ROOT/examples/icpc-onsite.toml" ]]; then
    cp "$REPO_ROOT/examples/icpc-onsite.toml" "$STAGING/boot/gallos/gallos.toml"
fi
cat > "$STAGING/boot/grub/grub.cfg" <<EOF
set default=0
set timeout=5

menuentry "GallosOS Live (walking skeleton)" {
    search --no-floppy --set=root --label $VOLID
    linux /casper/vmlinuz boot=casper console=ttyS0,115200n8 ipv6.disable=1
    initrd /casper/initrd
}
EOF

echo "Assembling hybrid ISO -> $OUT_ISO..."
mkdir -p "$(dirname "$OUT_ISO")"
grub-mkrescue -o "$OUT_ISO" "$STAGING" -- -volid "$VOLID"

echo "Stage 5b complete: $OUT_ISO"
