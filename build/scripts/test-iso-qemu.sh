#!/usr/bin/env bash
# test-iso-qemu.sh — Boot the GallosOS ISO in QEMU/KVM for rapid testing.
# Usage:
#   bash scripts/test-iso-qemu.sh                  # Legacy BIOS (fast)
#   bash scripts/test-iso-qemu.sh --uefi           # UEFI (SecureBoot-compatible path)
#   bash scripts/test-iso-qemu.sh --iso /path/to/other.iso
#   bash scripts/test-iso-qemu.sh --toram          # append toram to the kernel cmdline
#   bash scripts/test-iso-qemu.sh --usb-image /path/to/disk.img  # attach a synthetic USB disk
# Requires: qemu-system-x86_64, edk2-ovmf (for --uefi)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ISO="${REPO_ROOT}/build/output/gallosos-icpc-amd64.iso"
UEFI=0
TORAM=0
USB_IMAGE=""
OVMF_CODE="/usr/share/edk2/ovmf/OVMF_CODE.fd"
MEM="4096"
CPUS="2"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uefi)      UEFI=1 ;;
        --iso)       shift; ISO="$1" ;;
        --mem)       shift; MEM="$1" ;;
        --toram)     TORAM=1 ;;
        --usb-image) shift; USB_IMAGE="$1" ;;
        *)      echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

if [[ ! -f "$ISO" ]]; then
    echo "ERROR: ISO not found at $ISO"
    echo "Run 'make iso CONFIG=profiles/icpc.toml' first (or pass --iso for a different profile's output)."
    exit 1
fi
if [[ -n "$USB_IMAGE" && ! -f "$USB_IMAGE" ]]; then
    echo "ERROR: USB image not found at $USB_IMAGE"
    echo "Run 'bash build/scripts/make-test-usb-image.sh $USB_IMAGE' first."
    exit 1
fi

echo "============================================="
echo " GallosOS ISO QEMU Test"
echo "============================================="
echo " ISO   : $ISO"
echo " Mode  : $([ $UEFI -eq 1 ] && echo 'UEFI' || echo 'Legacy BIOS')"
echo " toram : $([ $TORAM -eq 1 ] && echo 'yes' || echo 'no')"
echo " USB   : ${USB_IMAGE:-none}"
echo " RAM   : ${MEM} MB  |  CPUs: ${CPUS}"
echo "============================================="

QEMU_ARGS=(
    -enable-kvm
    -m "$MEM"
    -smp "$CPUS"
    -cpu host
    -vga virtio
    -display gtk
    -netdev "user,id=net0"
    -device "virtio-net-pci,netdev=net0"
    -device "usb-ehci,id=ehci"
    -usb
    -device usb-tablet
)

if [[ $TORAM -eq 1 ]]; then
    # The ISO's own grub.cfg (build/scripts/build-iso.sh) hardcodes its
    # kernel cmdline, so testing an extra boot parameter means bypassing
    # GRUB: extract /casper/{vmlinuz,initrd} straight out of the ISO9660
    # filesystem with xorriso (no loop-mount / root privileges needed)
    # and boot them directly via QEMU's -kernel/-initrd/-append, mirroring
    # build-iso.sh's own cmdline plus toram.
    EXTRACT_DIR="$(mktemp -d)"
    trap 'rm -rf "$EXTRACT_DIR"' EXIT
    xorriso -indev "$ISO" -osirrox on \
        -extract /casper/vmlinuz "$EXTRACT_DIR/vmlinuz" \
        -extract /casper/initrd "$EXTRACT_DIR/initrd" \
        >/dev/null
    QEMU_ARGS+=(
        -kernel "$EXTRACT_DIR/vmlinuz"
        -initrd "$EXTRACT_DIR/initrd"
        -append "boot=casper console=ttyS0,115200n8 ipv6.disable=1 toram"
        -cdrom "$ISO"
    )
else
    QEMU_ARGS+=(-cdrom "$ISO" -boot d)
fi

if [[ -n "$USB_IMAGE" ]]; then
    QEMU_ARGS+=(-drive "if=none,id=gallosusb,format=raw,file=$USB_IMAGE" -device "usb-storage,drive=gallosusb")
fi

if [[ $UEFI -eq 1 ]]; then
    if [[ ! -f "$OVMF_CODE" ]]; then
        echo "ERROR: OVMF not found at $OVMF_CODE"
        echo "Install with: sudo dnf install -y edk2-ovmf"
        exit 1
    fi
    QEMU_ARGS+=(-bios "$OVMF_CODE")
fi

echo "Launching QEMU..."
# Not exec'd: the --toram EXTRACT_DIR cleanup trap above needs this shell
# to still be alive when qemu exits.
qemu-system-x86_64 "${QEMU_ARGS[@]}"
