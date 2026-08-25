"""Unit tests for GallosOS Daemon root recovery access module."""

import subprocess
from unittest.mock import patch

from daemon.src.root_access import set_root_password


def test_set_root_password_applies_hash():
    with patch("subprocess.run") as mock_run:
        set_root_password("$6$abc$def")
        mock_run.assert_called_once_with(
            ["chpasswd", "-e"], input="root:$6$abc$def\n", text=True, check=True
        )


def test_set_root_password_none_locks_root():
    with patch("subprocess.run") as mock_run:
        set_root_password(None)
        mock_run.assert_called_once_with(["passwd", "-l", "root"], check=False)


def test_set_root_password_empty_string_locks_root():
    with patch("subprocess.run") as mock_run:
        set_root_password("")
        mock_run.assert_called_once_with(["passwd", "-l", "root"], check=False)


def test_set_root_password_handles_chpasswd_failure_gracefully():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["chpasswd", "-e"])):
        set_root_password("$6$malformed")  # must not raise
