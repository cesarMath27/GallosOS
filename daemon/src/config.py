"""Config ingestion and validation module for GallosOS Daemon.

Handles hybrid config ingestion (remote URL with 5-second timeout,
fallback to local /boot/gallos/gallos.toml or /gallos/gallos.toml on Ventoy).
"""

import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

import tomllib

UTC_TZ_OFFSET = "+00:00"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1.0",
    "mode": "Default",
    "global": {
        "event_name": "GallosOS Live Session",
        "timezone": "UTC",
        "keyboard_layout": "us",
    },
    "default": {
        "allow_internet": True,
        "allow_usb_storage": True,
        "wallpaper_url": "",
    },
    "contest": {
        "allowed_websites": [],
        "allowed_tcp_ports": [80, 443],
        "allow_usb_storage": False,
        "wallpaper_url": "",
    },
    "event": {
        "allow_internet": True,
        "allow_usb_storage": True,
    },
}


def get_cmdline_config_param() -> str | None:
    """Extracts gallos.config parameter from /proc/cmdline if present."""
    if not os.path.exists("/proc/cmdline"):
        return None
    try:
        with open("/proc/cmdline", encoding="utf-8") as f:
            cmdline = f.read()
        for token in cmdline.split():
            if token.startswith("gallos.config="):
                return token.split("=", 1)[1]
    except Exception as e:
        print(f"[config] Error reading /proc/cmdline: {e}", file=sys.stderr)
    return None


def fetch_remote_config(url: str, timeout_sec: int = 5) -> str | None:
    """Fetches remote gallos.toml content over HTTP/HTTPS with timeout."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(
            f"[config] Refusing non-HTTP(S) config scheme '{parsed.scheme}': {url}",
            file=sys.stderr,
        )
        return None

    print(f"[config] Fetching remote config from: {url} (timeout={timeout_sec}s)")
    req = urllib.request.Request(url, headers={"User-Agent": "GallosOS-Daemon/0.2.0"})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            if resp.status == 200:
                return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[config] Remote config fetch failed: {e}", file=sys.stderr)
    return None


def _load_cmdline_config(cmdline_target: str) -> tuple[dict[str, Any] | None, str]:
    """Loads configuration specified via kernel cmdline parameter."""
    parsed = urllib.parse.urlparse(cmdline_target)
    if parsed.scheme in ("http", "https"):
        raw_toml = fetch_remote_config(cmdline_target, timeout_sec=5)
        if raw_toml:
            try:
                return tomllib.loads(raw_toml), f"remote ({cmdline_target})"
            except Exception as e:
                print(f"[config] Failed to parse remote TOML: {e}", file=sys.stderr)
        return None, ""

    if os.path.isfile(cmdline_target):
        try:
            with open(cmdline_target, "rb") as f:
                return tomllib.load(f), f"cmdline file ({cmdline_target})"
        except Exception as e:
            print(f"[config] Error reading {cmdline_target}: {e}", file=sys.stderr)

    return None, ""


def load_local_config() -> tuple[dict[str, Any] | None, str]:
    """Finds and loads the primary local gallos.toml config file."""
    candidates = [
        "/boot/gallos/gallos.toml",
        "/gallos/gallos.toml",  # Ventoy root directory
        "/etc/gallos/gallos.toml",
        "/usr/share/gallos/gallos.toml",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                print(f"[config] Loaded local configuration from {path}")
                return data, path
            except Exception as e:
                print(f"[config] Failed to parse {path}: {e}", file=sys.stderr)
    return None, ""


def load_machine_config() -> dict[str, Any]:
    """Finds and loads per-machine machine.toml configuration if present."""
    candidates = [
        "/boot/gallos/machine.toml",
        "/gallos/machine.toml",
        "/etc/gallos/machine.toml",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                print(f"[config] Loaded machine identity from {path}")
                return data
            except Exception as e:
                print(f"[config] Failed to parse {path}: {e}", file=sys.stderr)
    return {}


def is_config_expired(config: dict[str, Any]) -> bool:
    """Checks if the global.config_expiration timestamp has passed."""
    global_cfg = config.get("global", {})
    exp_str = global_cfg.get("config_expiration")
    if not exp_str:
        return False
    try:
        normalized = exp_str.replace("Z", UTC_TZ_OFFSET)
        exp_dt = datetime.fromisoformat(normalized)
        now_dt = datetime.now(timezone.utc)
        if now_dt > exp_dt:
            print(f"[config] Configuration expired at {exp_dt} (Current: {now_dt})")
            return True
    except Exception as e:
        print(f"[config] Error parsing config_expiration '{exp_str}': {e}", file=sys.stderr)
    return False


def load_active_config() -> dict[str, Any]:
    """Main entry point to obtain the active, validated configuration dictionary."""
    config_data: dict[str, Any] | None = None
    source_name = "built-in default"

    cmdline_target = get_cmdline_config_param()
    if cmdline_target:
        config_data, source_name = _load_cmdline_config(cmdline_target)

    if not config_data:
        config_data, source_name = load_local_config()

    if not config_data:
        print("[config] No external config found. Using default profile.")
        config_data = DEFAULT_CONFIG.copy()
        source_name = "default internal"

    if is_config_expired(config_data):
        print("[config] WARNING: Config is expired! Reverting to Default mode.")
        config_data["mode"] = "Default"

    print(f"[config] Active configuration source: {source_name}")
    return config_data
