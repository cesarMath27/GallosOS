"""Unit tests for gallos-daemon config ingestion module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import mock_open, patch

from daemon.src.config import (
    DEFAULT_CONFIG,
    fetch_remote_config,
    get_cmdline_config_param,
    is_config_expired,
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
