"""Desktop integration module for GallosOS Daemon.

Bridges the root-side daemon and the contestant's Wayland kiosk session
(build/desktop/, docs/WAYLAND_DESKTOP.md):

- wallpaper transitions: the wanted image path is published to
  /run/gallos/wallpaper and applied inside the session by the
  ``gallos-wallpaper --watch`` helper started from labwc's autostart (a
  direct swaybg spawn from the sandboxed root daemon is kept as a fallback);
- high-priority notifications via Mako (``notify-send`` as ``contestant``);
- real-time status for Waybar's custom modules (/run/gallos/state.json,
  read by ``gallos-waybar-status``);
- keyboard-layout environment for the kiosk launcher (/run/gallos/desktop.env,
  sourced by /etc/profile.d/gallos-kiosk.sh before labwc starts).
"""

import json
import os
import pwd
import re
import subprocess
import sys
from typing import Any

CONTESTANT_USER = "contestant"
RUN_DIR = "/run/gallos"
STATE_FILE = f"{RUN_DIR}/state.json"
WALLPAPER_FILE = f"{RUN_DIR}/wallpaper"
DESKTOP_ENV_FILE = f"{RUN_DIR}/desktop.env"

WALLPAPER_DIR = "/usr/share/backgrounds/gallos"
MODE_WALLPAPERS = {
    "Default": f"{WALLPAPER_DIR}/default.png",
    "Event": f"{WALLPAPER_DIR}/event.png",
    "Contest": f"{WALLPAPER_DIR}/contest.png",
}

# XKB group-toggle options: Super+Space and Alt+Shift cycle layouts inside
# the compositor itself (docs/WAYLAND_DESKTOP.md §4.1). Must match the
# fallback in build/desktop/etc/profile.d/gallos-kiosk.sh.
XKB_GROUP_TOGGLE_OPTIONS = "grp:win_space_toggle,grp:alt_shift_toggle"
FALLBACK_LAYOUTS = ["latam", "us", "es", "br"]
_XKB_LAYOUT_RE = re.compile(r"^[a-z0-9_]{1,16}$")


def _contestant_uid() -> int:
    try:
        return pwd.getpwnam(CONTESTANT_USER).pw_uid
    except KeyError:
        return 1000


def _session_env_prefix() -> str:
    """`env ...` prefix so a command run via `su - contestant` reaches the
    contestant's Wayland socket and (systemd user) D-Bus session bus."""
    runtime_dir = f"/run/user/{_contestant_uid()}"
    return (
        f"env XDG_RUNTIME_DIR={runtime_dir} WAYLAND_DISPLAY=wayland-0 "
        f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime_dir}/bus "
    )


def _write_run_file(path: str, content: str) -> bool:
    try:
        os.makedirs(RUN_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[desktop] Error writing {path}: {e}", file=sys.stderr)
        return False


def resolve_wallpaper(mode: str, custom_path: str = "") -> str:
    """Returns the wallpaper image for a mode; a custom local file wins."""
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    return MODE_WALLPAPERS.get(mode, MODE_WALLPAPERS["Default"])


def update_wallpaper(mode: str, custom_url: str = "") -> None:
    """Switches desktop wallpaper according to mode."""
    wallpaper_path = resolve_wallpaper(mode, custom_url)
    print(f"[desktop] Updating desktop wallpaper to: {wallpaper_path}")

    # Primary path: the in-session watcher (gallos-wallpaper --watch) picks
    # this file up within a couple of seconds and restarts swaybg itself.
    _write_run_file(WALLPAPER_FILE, wallpaper_path + "\n")

    # Fallback: spawn swaybg directly under the contestant's session.
    try:
        subprocess.run(["pkill", "-x", "swaybg"], check=False)
        cmd = f"{_session_env_prefix()}swaybg -i {wallpaper_path} -m fill &"
        subprocess.Popen(
            ["su", "-", CONTESTANT_USER, "-c", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[desktop] Error updating wallpaper: {e}", file=sys.stderr)


def send_desktop_notification(title: str, message: str, urgency: str = "normal") -> None:
    """Dispatches a desktop notification to Mako."""
    print(f"[desktop] Notification [{urgency}]: {title} - {message}")
    try:
        notify_body = (
            f"{_session_env_prefix()}notify-send -u {urgency} -a GallosOS '{title}' '{message}'"
        )
        cmd = ["su", "-", CONTESTANT_USER, "-c", notify_body]
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"[desktop] Error sending notification: {e}", file=sys.stderr)


def export_waybar_state(mode: str, remaining_seconds: int = 0) -> None:
    """Writes /run/gallos/state.json for Waybar custom status modules."""
    if remaining_seconds > 0:
        mins, secs = divmod(remaining_seconds, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        time_str = "Standby"

    payload = {
        "mode": mode,
        "badge": f"MODE: {mode.upper()}",
        "time_str": f"⏳ {time_str}",
        "remaining_sec": remaining_seconds,
        "wallpaper": MODE_WALLPAPERS.get(mode, MODE_WALLPAPERS["Default"]),
    }
    _write_run_file(STATE_FILE, json.dumps(payload))


def keyboard_layouts_from_config(config: dict[str, Any]) -> list[str]:
    """Ordered XKB layout list: the default layout first, then the others.

    Reads gallos.toml's [global] available_keyboard_layouts /
    default_keyboard_layout (schema/directives.schema.json); tolerates the
    daemon's own legacy `keyboard_layout` default. Unknown-looking tokens are
    dropped so nothing but plain XKB layout codes reaches the environment.
    """
    global_cfg = config.get("global", {}) or {}
    default = global_cfg.get("default_keyboard_layout") or global_cfg.get("keyboard_layout") or ""
    available = global_cfg.get("available_keyboard_layouts") or []
    if not isinstance(available, list):
        available = []

    ordered: list[str] = []
    for token in [default, *available]:
        token = str(token).strip().lower()
        if token and _XKB_LAYOUT_RE.match(token) and token not in ordered:
            ordered.append(token)
    return ordered or list(FALLBACK_LAYOUTS)


def export_desktop_env(config: dict[str, Any]) -> None:
    """Writes /run/gallos/desktop.env, sourced by the kiosk launcher."""
    layouts = ",".join(keyboard_layouts_from_config(config))
    content = (
        "# Generated by gallos-daemon (daemon/src/desktop.py); sourced by\n"
        "# /etc/profile.d/gallos-kiosk.sh before labwc starts.\n"
        f"XKB_DEFAULT_LAYOUT={layouts}\n"
        f"XKB_DEFAULT_OPTIONS={XKB_GROUP_TOGGLE_OPTIONS}\n"
    )
    if _write_run_file(DESKTOP_ENV_FILE, content):
        print(f"[desktop] Keyboard layouts exported for the kiosk session: {layouts}")
