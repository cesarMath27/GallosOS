#!/usr/bin/env bash
# Stage 3: Stripping & Optimization (docs/BUILD_SYSTEM.md §3), driven by
# build.toml's [optimization] table. Every directive is opt-in: a
# false/absent flag leaves that step a no-op.
set -euo pipefail

CONFIG="$1"
ROOTFS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=build/scripts/lib-chroot.sh
source "$SCRIPT_DIR/lib-chroot.sh"

strip_man="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" optimization.strip_man_pages)"
strip_docs="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" optimization.strip_docs)"
remove_apt_cache="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" optimization.remove_apt_cache)"
mapfile -t locales < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" optimization.locales)

chroot_mount "$ROOTFS"
trap 'chroot_umount "$ROOTFS"' EXIT

if [[ "$strip_man" == "true" ]]; then
    echo "Stripping man pages..."
    rm -rf "$ROOTFS"/usr/share/man/*
fi

if [[ "$strip_docs" == "true" ]]; then
    echo "Stripping docs..."
    rm -rf "$ROOTFS"/usr/share/doc/*
fi

if [[ ${#locales[@]} -gt 0 ]]; then
    echo "Regenerating locales: ${locales[*]}"
    locale_gen_lines=""
    for loc in "${locales[@]}"; do
        locale_gen_lines+="$loc UTF-8\n"
    done
    chroot "$ROOTFS" /bin/bash -euxc "
        printf '$locale_gen_lines' > /etc/locale.gen
        locale-gen
        update-locale LANG='${locales[0]}'
    "
fi

if [[ "$remove_apt_cache" == "true" ]]; then
    echo "Purging apt cache..."
    chroot "$ROOTFS" apt-get clean
    rm -rf "$ROOTFS"/var/lib/apt/lists/*
fi

echo "Stage 3 complete."
