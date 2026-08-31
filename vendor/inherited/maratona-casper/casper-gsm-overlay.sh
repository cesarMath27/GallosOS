#!/bin/sh
# GallosOS build-time patch for the installed Ubuntu `casper` package's
# initramfs-tools live-boot script (ROADMAP.md Phase 1 "Casper Live Boot
# Engine": mount SquashFS .gsm modules into the OverlayFS union layers).
#
# Why a patch applied at build time, not a casper-bottom hook: by the time
# casper-bottom hooks (55gallos-live) run, casper's own setup_overlay()
# has already assembled and mounted the union overlay — casper-bottom
# cannot inject new lowerdir= layers after the fact. The mount logic has
# to be added inside setup_overlay() itself, one stage earlier. See
# 55gallos-live's own header comment and docs/BUILD_SYSTEM.md's Tier 2/3
# module-stacking spec for the target layout being reproduced here:
#   <medium>/gallos/modules/*.gsm         (Tier 2, sorted stacking order)
#   <medium>/gallos/system/99-custom.gsm  (Tier 3, reserved top layer)
#
# Anchored on exact lines from the Ubuntu 24.04 `casper` package as
# installed by build/scripts/02-provision.sh. Fails loudly (non-zero exit)
# if the anchors are missing, rather than silently no-op'ing, so a future
# casper package version bump breaks the build instead of shipping an ISO
# that silently can't mount software modules. Uses awk for literal (not
# regex) line matching and insertion — no sed delimiter/escaping games,
# since the anchor lines themselves contain shell glob/case-pattern
# characters that would otherwise collide with sed's own syntax.
#
# Usage: sh casper-gsm-overlay.sh <path-to-installed-casper-script>

# shellcheck shell=sh
# shellcheck disable=SC1007,SC2016
# SC1007: `CDPATH= cd --` intentionally clears CDPATH before cd (standard
#   idiom), not a mistaken assignment.
# SC2016: LOOP_ANCHOR/BACKDEV_ANCHOR are meant to hold literal, unexpanded
#   text — they're compared verbatim against lines in the target script.

set -eu

CASPER_SCRIPT="${1:-}"
if [ -z "$CASPER_SCRIPT" ] || [ ! -f "$CASPER_SCRIPT" ]; then
    echo "casper-gsm-overlay.sh: usage: $0 <path-to-casper-script>" >&2
    exit 1
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
INSERT_FILE="$SCRIPT_DIR/casper-gsm-overlay.insert.sh"

BACKDEV_ANCHOR='        *.squashfs|*.ext2)'
BACKDEV_REPLACEMENT='        *.squashfs|*.ext2|*.gsm)'
LOOP_ANCHOR='    rofsstring=${rofsstring%:}'

if [ ! -f "$INSERT_FILE" ]; then
    echo "casper-gsm-overlay.sh: missing companion file $INSERT_FILE" >&2
    exit 1
fi
if ! grep -qF "$BACKDEV_ANCHOR" "$CASPER_SCRIPT"; then
    echo "casper-gsm-overlay.sh: get_backing_device() anchor not found in $CASPER_SCRIPT — casper package layout changed, patch needs updating." >&2
    exit 1
fi
if ! grep -qF "$LOOP_ANCHOR" "$CASPER_SCRIPT"; then
    echo "casper-gsm-overlay.sh: setup_overlay() anchor not found in $CASPER_SCRIPT — casper package layout changed, patch needs updating." >&2
    exit 1
fi

# 1. Treat *.gsm like *.squashfs in get_backing_device()'s case pattern —
#    a .gsm file IS a SquashFS image under a different extension, so the
#    existing setup_loop/blkid-based fstype detection works unmodified.
# 2. Insert the .gsm module-mounting loop into setup_overlay(), right
#    before the base-image loop's rofsstring is trimmed of its trailing
#    colon (see casper-gsm-overlay.insert.sh for the inserted code and
#    why it's ordered to give modules priority over the base image).
awk -v backdev_anchor="$BACKDEV_ANCHOR" \
    -v backdev_replacement="$BACKDEV_REPLACEMENT" \
    -v loop_anchor="$LOOP_ANCHOR" \
    -v insert_file="$INSERT_FILE" '
    $0 == backdev_anchor {
        print backdev_replacement
        next
    }
    $0 == loop_anchor {
        while ((getline line < insert_file) > 0) {
            print line
        }
        close(insert_file)
        print
        next
    }
    { print }
' "$CASPER_SCRIPT" > "${CASPER_SCRIPT}.gallos-tmp"
mv "${CASPER_SCRIPT}.gallos-tmp" "$CASPER_SCRIPT"

echo "casper-gsm-overlay.sh: patched $CASPER_SCRIPT for .gsm module mounting."
