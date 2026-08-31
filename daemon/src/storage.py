"""Event-data partition mount/unmount for GallosOS Daemon.

Mounts the optional `event-data` ext4 partition by filesystem label only —
never by partition number or offset — since gallos-flash's 2-partition
GALLOS_BOOT + event-data layout and Ventoy's exFAT+EFI+reserved-region
layout place it at different offsets (docs/ARCHITECTURE.md §4 item 5).
Contest mode never mounts event-data; Default and Event modes do, so mode
transitions in state_machine.py own the mount/unmount calls, not casper.
"""

import os
import subprocess
import sys

EVENT_DATA_LABEL = "event-data"
EVENT_DATA_MOUNTPOINT = "/media/event-data"


def _find_event_data_device() -> str | None:
    """Resolves the event-data partition's device node by filesystem label."""
    try:
        result = subprocess.run(
            ["blkid", "-L", EVENT_DATA_LABEL],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    device = result.stdout.strip()
    return device or None


def mount_event_data() -> bool:
    """Mounts the event-data partition at /media/event-data if present.

    A no-op that returns True when no event-data-labeled partition exists —
    the partition is optional per docs/ARCHITECTURE.md §4 item 5.
    """
    if os.path.ismount(EVENT_DATA_MOUNTPOINT):
        return True

    device = _find_event_data_device()
    if not device:
        return True

    os.makedirs(EVENT_DATA_MOUNTPOINT, exist_ok=True)
    result = subprocess.run(
        ["mount", "-t", "ext4", device, EVENT_DATA_MOUNTPOINT],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"[storage] Failed to mount event-data ({device}): {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    print(f"[storage] Mounted event-data ({device}) at {EVENT_DATA_MOUNTPOINT}")
    return True


def unmount_event_data() -> None:
    """Lazily unmounts /media/event-data if mounted."""
    subprocess.run(["umount", "-l", EVENT_DATA_MOUNTPOINT], check=False)
