"""Unit tests for gallos-daemon event-data partition mount/unmount module."""

from unittest.mock import MagicMock, patch

from daemon.src.storage import (
    EVENT_DATA_MOUNTPOINT,
    mount_event_data,
    unmount_event_data,
)


def test_mount_event_data_already_mounted():
    with patch("os.path.ismount", return_value=True):
        with patch("subprocess.run") as mock_run:
            assert mount_event_data() is True
            mock_run.assert_not_called()


def test_mount_event_data_no_partition_found():
    with patch("os.path.ismount", return_value=False):
        with patch("subprocess.run", return_value=MagicMock(stdout="")) as mock_run:
            assert mount_event_data() is True
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0][:2] == ["blkid", "-L"]


def test_mount_event_data_mounts_found_device():
    blkid_result = MagicMock(stdout="/dev/sdb2\n")
    mount_result = MagicMock(returncode=0)
    with patch("os.path.ismount", return_value=False):
        with patch("os.makedirs") as mock_makedirs:
            with patch("subprocess.run", side_effect=[blkid_result, mount_result]) as mock_run:
                assert mount_event_data() is True
                mock_makedirs.assert_called_once_with(EVENT_DATA_MOUNTPOINT, exist_ok=True)
                mount_cmd = mock_run.call_args_list[1][0][0]
                assert mount_cmd[:2] == ["mount", "-t"]
                assert "/dev/sdb2" in mount_cmd


def test_mount_event_data_mount_failure_returns_false():
    blkid_result = MagicMock(stdout="/dev/sdb2\n")
    mount_result = MagicMock(returncode=1, stderr="mount failed")
    with patch("os.path.ismount", return_value=False):
        with patch("os.makedirs"):
            with patch("subprocess.run", side_effect=[blkid_result, mount_result]):
                assert mount_event_data() is False


def test_unmount_event_data():
    with patch("subprocess.run") as mock_run:
        unmount_event_data()
        mock_run.assert_called_once_with(["umount", "-l", EVENT_DATA_MOUNTPOINT], check=False)
