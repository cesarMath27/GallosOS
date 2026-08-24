#!/usr/bin/env bash
# Stage 2: Provisioning (docs/BUILD_SYSTEM.md §3).
#
# Chroots into $ROOTFS and: installs a kernel + casper live-boot machinery,
# installs the GallosOS casper-bottom hook, and applies build.toml's
# [packages].preinstall_apt list.
#
# NOT in this pass (deferred to the next increment, see the approved plan):
#   - Wayland kiosk core (labwc/waybar/foot)
#   - gallos-daemon injection (its functional scope is Phase 3)
set -euo pipefail

CONFIG="$1"
ROOTFS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=build/scripts/lib-chroot.sh
source "$SCRIPT_DIR/lib-chroot.sh"

kernel_pkg="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.kernel)"
mapfile -t extra_pkgs < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" packages.preinstall_apt)

chroot_mount "$ROOTFS"
# Deliberately not unmounted here: 03-optimize.sh chroots into the same
# rootfs next within the same container run and re-mounting /sys there
# fails ("already mounted"). chroot_umount runs once, at the end of
# 03-optimize.sh, after every chroot-dependent stage is done.

chroot "$ROOTFS" /bin/bash -euxc "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    # Expect: 'debconf: Unknown template field help, in stanza N of
    # .../localechooser-data.template...' during this install. casper pulls
    # in user-setup which pulls in localechooser-data (real noble/main
    # package); its debconf templates carry a help field meant for the
    # graphical/text Debian installer's on-screen help, which the plain
    # chroot debconf frontend does not recognize. Benign upstream Ubuntu
    # packaging quirk, unrelated to this pipeline — the package still
    # unpacks and configures cleanly right after.
    apt-get install -y --no-install-recommends \
        '$kernel_pkg' \
        casper \
        initramfs-tools \
        systemd-sysv \
        network-manager \
        locales \
        plymouth \
        plymouth-theme-ubuntu-text \
        zstd \
        ${extra_pkgs[*]@Q}

    # Expect several benign warnings during the installs above, all of them
    # standard installing-inside-a-build-chroot behavior seen on any
    # debootstrap/live-build pipeline, not GallosOS-specific:
    #   - policy-rc.d/dbus: 'Running in chroot, ignoring request.' and
    #     'Failed to open connection to system message bus' (polkitd,
    #     network-manager) - postinst scripts reaching for a live dbus/
    #     service daemon that is not running inside a build chroot.
    #   - NetworkManager: 'Could not create NMClient object' / 'could not
    #     reload connections' - same cause, NetworkManager's own postinst.
    #   - systemd tmpfiles: 'Failed to resolve group polkitd' - systemd is
    #     configured before polkitd in this install order, so its tmpfiles
    #     rule referencing that group cannot resolve yet; resolves for real
    #     at actual boot (already verified working).
    #   - update-rc.d (plymouth): 'start and stop actions are no longer
    #     supported' - old SysV-init postinst syntax hitting the modern
    #     compat shim, a standard deprecation notice on any real install.
    #   - udev: 'fchownat()/fchmod() of /dev/... failed: Operation not
    #     permitted' - same CAP_MKNOD-adjacent restriction documented in
    #     01-bootstrap.sh's debootstrap note: these are bind-mounted device
    #     nodes from the container's own /dev, which rootless Podman denies
    #     permission changes on. Cosmetic for build-time /dev; the real
    #     target kernel/udev creates and permissions its own device tree
    #     at actual boot (already verified working).

    echo 'gallos-live' > /etc/hostname

    # Overlay/squashfs/isofs modules must be present in the initrd for casper
    # to assemble the live root — see vendor/inherited/maratona-casper/55gallos-live.
    { echo overlay; echo squashfs; echo isofs; echo vfat; } >> /etc/initramfs-tools/modules

    # Walking-skeleton verification only: autologin on both the serial
    # console (ttyS0, for headless QEMU -nographic -serial mon:stdio boot
    # tests — see the plan's Verification section) and the graphical
    # console (tty1, for plain 'qemu-system-x86_64 ... -boot d' with a
    # display window — contestant has no password set, so without this
    # tty1's normal login prompt cannot be satisfied at all). This is NOT a
    # production/anti-cheat-safe configuration — Phase 2 locks this down.
    useradd -m -s /bin/bash contestant || true
    mkdir -p /etc/systemd/system/serial-getty@ttyS0.service.d
    cat > /etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I \$TERM
EOF
    mkdir -p /etc/systemd/system/getty@tty1.service.d
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I \$TERM
EOF
"

# The casper-bottom directory only exists once the casper/initramfs-tools
# packages above are installed, and the source file lives outside $ROOTFS
# (invisible from inside the chroot) — so this copy has to happen from the
# host side, between package install and the initramfs regen below.
echo "Installing casper hook: 55gallos-live"
install -m 0755 \
    "$REPO_ROOT/vendor/inherited/maratona-casper/55gallos-live" \
    "$ROOTFS/usr/share/initramfs-tools/scripts/casper-bottom/55gallos-live"

chroot "$ROOTFS" update-initramfs -c -k all

echo "Stage 2 complete."
