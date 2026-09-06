#!/usr/bin/env bash
# Provisioning stage: installs kernel, casper live-boot hooks, base utilities,
# and the Wayland kiosk desktop environment (labwc, waybar, foot, mako, swaybg).
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

# 1. Install packages inside chroot
chroot "$ROOTFS" /bin/bash -euxc "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends --fix-missing \
        '$kernel_pkg' \
        casper \
        initramfs-tools \
        systemd-sysv \
        network-manager \
        locales \
        plymouth \
        plymouth-theme-ubuntu-text \
        zstd \
        fonts-font-awesome \
        ${extra_pkgs[*]@Q}

    echo 'gallos-live' > /etc/hostname
    { echo overlay; echo squashfs; echo isofs; echo vfat; echo exfat; } >> /etc/initramfs-tools/modules

    # Create contestant user with video/input/render permissions
    useradd -m -s /bin/bash contestant || true
    usermod -a -G video,input,render contestant || true
    if getent group _seatd >/dev/null 2>&1; then
        usermod -a -G _seatd contestant || true
    fi
"

# 2. Wayland kiosk desktop shell: dotfiles + in-band helper scripts.
# Everything under build/desktop/ mirrors the target filesystem layout
# (/etc/xdg/{labwc,waybar,foot,mako}, /etc/profile.d/gallos-kiosk.sh,
# /usr/bin/gallos-*, /usr/share/gallos/) and is copied verbatim — see
# build/desktop/README.md and docs/WAYLAND_DESKTOP.md.
echo "Installing Wayland kiosk desktop overlay (build/desktop/)..."
cp -a "$REPO_ROOT/build/desktop/." "$ROOTFS/"
chmod 0755 "$ROOTFS"/usr/bin/gallos-* "$ROOTFS/etc/xdg/labwc/autostart"
chmod 0644 "$ROOTFS/etc/profile.d/gallos-kiosk.sh"
chown -R root:root "$ROOTFS/etc/xdg" "$ROOTFS/usr/share/gallos" "$ROOTFS/etc/profile.d/gallos-kiosk.sh"

# Contestant workspace: seeded from /etc/skel so the Clean State Wipe
# (docs/CONFIG_SPEC.md § Mode Semantics) restores an empty ~/workspace too.
mkdir -p "$ROOTFS/etc/skel/workspace" "$ROOTFS/home/contestant/workspace"
chroot "$ROOTFS" chown -R contestant:contestant /home/contestant

# Mode wallpapers (default / event / contest), generated with the Python
# stdlib so the build container needs no image library and git holds no
# binary asset — see build/scripts/gen-wallpapers.py.
python3 "$SCRIPT_DIR/gen-wallpapers.py" "$ROOTFS/usr/share/backgrounds/gallos"

# Graphical Kiosk Autologin on tty1. The session itself is started by
# /etc/profile.d/gallos-kiosk.sh (from build/desktop/), which execs
# `labwc -C /etc/xdg/labwc` on tty1.
mkdir -p "$ROOTFS/etc/systemd/system/getty@tty1.service.d"
cat > "$ROOTFS/etc/systemd/system/getty@tty1.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I $TERM
EOF

# Serial console ttyS0 autologin for automated testing
mkdir -p "$ROOTFS/etc/systemd/system/serial-getty@ttyS0.service.d"
cat > "$ROOTFS/etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I $TERM
EOF

# Install casper live-boot hook
echo "Installing casper hook: 55gallos-live"
install -m 0755 \
    "$REPO_ROOT/vendor/inherited/maratona-casper/55gallos-live" \
    "$ROOTFS/usr/share/initramfs-tools/scripts/casper-bottom/55gallos-live"

# Patch casper's own scripts/casper to mount .gsm SquashFS software modules
# into the OverlayFS union (ROADMAP.md Phase 1 "Casper Live Boot Engine";
# see vendor/inherited/maratona-casper/casper-gsm-overlay.sh for why this
# must be a build-time patch to setup_overlay() rather than a casper-bottom
# hook). Fails the build loudly if the anchors it depends on have drifted.
echo "Patching casper for .gsm module mounting..."
sh "$REPO_ROOT/vendor/inherited/maratona-casper/casper-gsm-overlay.sh" \
    "$ROOTFS/usr/share/initramfs-tools/scripts/casper"

# Install gallos-daemon and gallos-ctl. Installed under the module name
# gallos_daemon (underscore, not gallos-daemon's hyphen) because main.py's
# sibling modules use package-relative imports (`from .config import ...`)
# — those only resolve when main.py is run as `python3 -m gallos_daemon.main`
# (see gallos-daemon.service's ExecStart/WorkingDirectory), and `-m` needs a
# syntactically valid Python package/module name.
echo "Installing gallos-daemon and gallos-ctl..."
mkdir -p "$ROOTFS/usr/libexec/gallos_daemon"
cp -r "$REPO_ROOT/daemon/src/"* "$ROOTFS/usr/libexec/gallos_daemon/"
chmod -R 0755 "$ROOTFS/usr/libexec/gallos_daemon"
install -m 0755 "$REPO_ROOT/daemon/gallos-ctl" "$ROOTFS/usr/bin/gallos-ctl"

chroot "$ROOTFS" update-initramfs -c -k all

echo "Stage 2 complete."
