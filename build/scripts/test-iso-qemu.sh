#!/usr/bin/env bash
# test-iso-qemu.sh — Boot the GallosOS ISO in QEMU/KVM for rapid testing.
# Usage:
#   bash scripts/test-iso-qemu.sh                  # Legacy BIOS (fast)
#   bash scripts/test-iso-qemu.sh --uefi           # UEFI (SecureBoot-compatible path)
#   bash scripts/test-iso-qemu.sh --iso /path/to/other.iso
# Requires: qemu-system-x86_64, edk2-ovmf (for --uefi)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ISO="${REPO_ROOT}/build/output/gallosOS-custom-amd64.iso"
UEFI=0
OVMF_CODE="/usr/share/edk2/ovmf/OVMF_CODE.fd"
MEM="4096"
CPUS="2"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uefi) UEFI=1 ;;
        --iso)  shift; ISO="$1" ;;
        --mem)  shift; MEM="$1" ;;
        *)      echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

if [[ ! -f "$ISO" ]]; then
    echo "ERROR: ISO not found at $ISO"
    echo "Run 'make iso CONFIG=profiles/build-icpc.toml' first."
    exit 1
fi

echo "============================================="
echo " GallosOS ISO QEMU Test"
echo "============================================="
echo " ISO   : $ISO"
echo " Mode  : $([ $UEFI -eq 1 ] && echo 'UEFI' || echo 'Legacy BIOS')"
echo " RAM   : ${MEM} MB  |  CPUs: ${CPUS}"
echo "============================================="

QEMU_ARGS=(
    -enable-kvm
    -m "$MEM"
    -smp "$CPUS"
    -cpu host
    -cdrom "$ISO"
    -boot d
    -vga virtio
    -display gtk
    -netdev user,id=net0
    -device virtio-net-pci,netdev=net0
    -device usb-ehci,id=ehci
    -usb
    -device usb-tablet
)

if [[ $UEFI -eq 1 ]]; then
    if [[ ! -f "$OVMF_CODE" ]]; then
        echo "ERROR: OVMF not found at $OVMF_CODE"
        echo "Install with: sudo dnf install -y edk2-ovmf"
        exit 1
    fi
    QEMU_ARGS+=(-bios "$OVMF_CODE")
fi

echo "Launching QEMU..."
exec qemu-system-x86_64 "${QEMU_ARGS[@]}"
