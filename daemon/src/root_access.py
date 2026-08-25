"""Root Recovery Access module for GallosOS Daemon.

Applies or clears a locally-declared root password hash for `su` recovery
access from within the kiosk session. No SSH/network component — see
docs/ROOT_ACCESS.md for the full design and its explicitly-deferred scope.
"""

import subprocess
import sys


def set_root_password(password_hash: str | None) -> None:
    """Applies the configured root password hash, or re-locks root if unset."""
    if password_hash:
        print("[root_access] Applying configured root password hash for local su recovery.")
        try:
            subprocess.run(
                ["chpasswd", "-e"],
                input=f"root:{password_hash}\n",
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[root_access] Failed to apply root password hash: {e}", file=sys.stderr)
    else:
        print("[root_access] No root password hash configured; keeping root locked.")
        subprocess.run(["passwd", "-l", "root"], check=False)
