"""Unit tests for gallos-daemon desktop integration (daemon/src/desktop.py)."""

import json
from unittest.mock import patch

from daemon.src import desktop


def test_resolve_wallpaper_per_mode(tmp_path):
    assert desktop.resolve_wallpaper("Default").endswith("/default.png")
    assert desktop.resolve_wallpaper("Event").endswith("/event.png")
    assert desktop.resolve_wallpaper("Contest").endswith("/contest.png")
    # Unknown mode falls back to the Default image.
    assert desktop.resolve_wallpaper("Weird").endswith("/default.png")


def test_resolve_wallpaper_prefers_existing_custom_file(tmp_path):
    custom = tmp_path / "branding.png"
    custom.write_bytes(b"png")
    assert desktop.resolve_wallpaper("Contest", str(custom)) == str(custom)
    # A missing custom path is ignored, not applied blindly.
    assert desktop.resolve_wallpaper("Contest", str(tmp_path / "nope.png")).endswith("/contest.png")


def test_update_wallpaper_publishes_path_and_spawns_swaybg(tmp_path):
    wallpaper_file = tmp_path / "wallpaper"
    with (
        patch.object(desktop, "RUN_DIR", str(tmp_path)),
        patch.object(desktop, "WALLPAPER_FILE", str(wallpaper_file)),
        patch.object(desktop, "_contestant_uid", return_value=1000),
        patch("daemon.src.desktop.subprocess.run") as mock_run,
        patch("daemon.src.desktop.subprocess.Popen") as mock_popen,
    ):
        desktop.update_wallpaper("Contest")

    # The session-side watcher (gallos-wallpaper --watch) reads this file.
    assert wallpaper_file.read_text().strip() == desktop.MODE_WALLPAPERS["Contest"]
    mock_run.assert_called_once_with(["pkill", "-x", "swaybg"], check=False)
    su_cmd = mock_popen.call_args.args[0]
    assert su_cmd[:3] == ["su", "-", "contestant"]
    assert "WAYLAND_DISPLAY=wayland-0" in su_cmd[-1]
    assert "XDG_RUNTIME_DIR=/run/user/1000" in su_cmd[-1]
    assert desktop.MODE_WALLPAPERS["Contest"] in su_cmd[-1]


def test_send_desktop_notification_targets_session_bus():
    with (
        patch.object(desktop, "_contestant_uid", return_value=1000),
        patch("daemon.src.desktop.subprocess.run") as mock_run,
    ):
        desktop.send_desktop_notification("Contest Ended", "USB unlocked", urgency="critical")
    cmd = mock_run.call_args.args[0]
    assert cmd[:3] == ["su", "-", "contestant"]
    assert "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" in cmd[-1]
    assert "notify-send -u critical -a GallosOS 'Contest Ended' 'USB unlocked'" in cmd[-1]


def test_export_waybar_state_payload(tmp_path):
    state_file = tmp_path / "state.json"
    with (
        patch.object(desktop, "RUN_DIR", str(tmp_path)),
        patch.object(desktop, "STATE_FILE", str(state_file)),
    ):
        desktop.export_waybar_state("Contest", 3725)
        payload = json.loads(state_file.read_text())
        assert payload["mode"] == "Contest"
        assert payload["remaining_sec"] == 3725
        assert payload["time_str"].endswith("01:02:05")
        assert payload["wallpaper"].endswith("/contest.png")

        desktop.export_waybar_state("Default", 0)
        payload = json.loads(state_file.read_text())
        assert payload["remaining_sec"] == 0
        assert payload["time_str"].endswith("Standby")


def test_keyboard_layouts_default_first_and_deduplicated():
    config = {
        "global": {
            "available_keyboard_layouts": ["latam", "us", "es"],
            "default_keyboard_layout": "us",
        }
    }
    assert desktop.keyboard_layouts_from_config(config) == ["us", "latam", "es"]


def test_keyboard_layouts_legacy_key_and_fallback():
    # Daemon's own DEFAULT_CONFIG shape (global.keyboard_layout only).
    assert desktop.keyboard_layouts_from_config({"global": {"keyboard_layout": "us"}}) == ["us"]
    # Nothing configured at all -> baked-in fallback cycle.
    assert desktop.keyboard_layouts_from_config({}) == desktop.FALLBACK_LAYOUTS


def test_keyboard_layouts_rejects_unsafe_tokens():
    config = {
        "global": {
            "available_keyboard_layouts": ["latam", "us; rm -rf /", "$(id)", "BR", ""],
            "default_keyboard_layout": "latam",
        }
    }
    assert desktop.keyboard_layouts_from_config(config) == ["latam", "br"]


def test_export_desktop_env_writes_xkb_variables(tmp_path):
    env_file = tmp_path / "desktop.env"
    config = {"global": {"available_keyboard_layouts": ["latam", "us"]}}
    with (
        patch.object(desktop, "RUN_DIR", str(tmp_path)),
        patch.object(desktop, "DESKTOP_ENV_FILE", str(env_file)),
    ):
        desktop.export_desktop_env(config)
    content = env_file.read_text()
    assert "XKB_DEFAULT_LAYOUT=latam,us\n" in content
    assert f"XKB_DEFAULT_OPTIONS={desktop.XKB_GROUP_TOGGLE_OPTIONS}\n" in content
