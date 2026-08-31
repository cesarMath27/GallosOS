"""Unit tests for gallos-daemon config ingestion module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import mock_open, patch

from daemon.src.config import (
    DEFAULT_CONFIG,
    fetch_remote_config,
    get_cmdline_config_param,
    is_config_expired,
    load_active_config,
    load_local_config,
    load_machine_config,
)


def test_default_config_structure():
    assert "version" in DEFAULT_CONFIG
    assert "mode" in DEFAULT_CONFIG
    assert "global" in DEFAULT_CONFIG
    assert "contest" in DEFAULT_CONFIG
    assert "default" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["mode"] == "Default"


def test_is_config_expired_not_set():
    config = {"global": {}}
    assert is_config_expired(config) is False


def test_is_config_expired_future():
    future_dt = datetime.now(timezone.utc) + timedelta(days=1)
    config = {"global": {"config_expiration": future_dt.isoformat()}}
    assert is_config_expired(config) is False


def test_is_config_expired_past():
    past_dt = datetime.now(timezone.utc) - timedelta(days=1)
    config = {"global": {"config_expiration": past_dt.isoformat()}}
    assert is_config_expired(config) is True


def test_get_cmdline_config_param():
    mock_cmdline = (
        "BOOT_IMAGE=/casper/vmlinuz boot=casper gallos.config=http://192.168.1.10/gallos.toml quiet"
    )
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=mock_cmdline)),
    ):
        param = get_cmdline_config_param()
        assert param == "http://192.168.1.10/gallos.toml"


def test_fetch_remote_config_rejects_non_http():
    assert fetch_remote_config("ftp://example.com/gallos.toml") is None
    assert fetch_remote_config("file:///etc/gallos.toml") is None


def test_load_active_config_ignores_remote_recovery_hash():
    """recovery.root_password_hash must never come from a remote/cmdline-fetched config."""
    remote_config = {
        "mode": "Default",
        "global": {},
        "recovery": {"root_password_hash": "$6$leaked$fromremote"},
    }
    with (
        patch("daemon.src.config.get_cmdline_config_param", return_value="http://x/gallos.toml"),
        patch(
            "daemon.src.config._load_cmdline_config",
            return_value=(remote_config, "remote (http://x/gallos.toml)"),
        ),
        patch(
            "daemon.src.config.load_local_config",
            return_value=(
                {"recovery": {"root_password_hash": "$6$local$hash"}},
                "/boot/gallos/gallos.toml",
            ),
        ),
    ):
        result = load_active_config()
        assert result["recovery"]["root_password_hash"] == "$6$local$hash"


def test_load_local_config_prefers_boot_gallos_config_dir():
    """The 55gallos-live /boot/gallos symlink target must win over flat-path fallbacks."""
    toml_bytes = b'mode = "Default"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/boot/gallos/config/gallos.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        data, source = load_local_config()
        assert source == "/boot/gallos/config/gallos.toml"
        assert data["mode"] == "Default"


def test_load_local_config_falls_back_to_ventoy_path():
    toml_bytes = b'mode = "Default"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/gallos/gallos.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        _, source = load_local_config()
        assert source == "/gallos/gallos.toml"


def test_load_machine_config_prefers_boot_gallos_config_dir():
    toml_bytes = b'hostname = "seat-04"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/boot/gallos/config/machine.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        data = load_machine_config()
        assert data["hostname"] == "seat-04"


def test_load_active_config_no_local_recovery_hash_defaults_to_none():
    with (
        patch("daemon.src.config.get_cmdline_config_param", return_value=None),
        patch("daemon.src.config.load_local_config", return_value=(None, "")),
    ):
        result = load_active_config()
        assert result["recovery"]["root_password_hash"] is None
