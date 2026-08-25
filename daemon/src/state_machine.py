"""3-Tier Mode State Machine (Contest > Event > Default) for GallosOS Daemon.

Evaluates scheduled time-windows, monotonic timers, and manual organizer triggers,
orchestrating the Clean State Wipe, dynamic firewall, USB lockdown, and desktop state.
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

from .browser_policy import apply_browser_policy
from .desktop import export_waybar_state, send_desktop_notification, update_wallpaper
from .firewall import FirewallManager
from .usb_manager import set_usb_storage_allowed

UTC_TZ_OFFSET = "+00:00"


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parses an ISO 8601 string, normalizing UTC 'Z' indicator to '+00:00'."""
    normalized = dt_str.replace("Z", UTC_TZ_OFFSET)
    return datetime.fromisoformat(normalized)


def _wipe_directory_contents(dir_path: str) -> None:
    """Removes all files, symlinks, and subdirectories within dir_path."""
    if not os.path.isdir(dir_path):
        return
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        try:
            if os.path.isdir(item_path) and not os.path.islink(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        except Exception as e:
            print(f"[state_machine] Error removing {item_path}: {e}", file=sys.stderr)


def _populate_from_skel(skel_dir: str, target_dir: str) -> None:
    """Restores default files and directories from skeleton template."""
    if not os.path.isdir(skel_dir):
        return
    for item in os.listdir(skel_dir):
        src = os.path.join(skel_dir, item)
        dst = os.path.join(target_dir, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(f"[state_machine] Error copying skeleton item {src}: {e}", file=sys.stderr)


def perform_clean_state_wipe() -> None:
    """Executes the Clean State Wipe on Contest entry."""
    print("[state_machine] Performing destructive Clean State Wipe of /home/contestant/...")
    home_dir = "/home/contestant"
    skel_dir = "/etc/skel"
    try:
        subprocess.run(["pkill", "-KILL", "-u", "contestant"], check=False)
        time.sleep(0.5)
        _wipe_directory_contents(home_dir)
        _populate_from_skel(skel_dir, home_dir)
        subprocess.run(["chown", "-R", "contestant:contestant", home_dir], check=False)
        print("[state_machine] Clean State Wipe completed successfully.")
    except Exception as e:
        print(f"[state_machine] Error during Clean State Wipe: {e}", file=sys.stderr)


def _is_schedule_active(schedule_dict: dict[str, Any], now_utc: datetime) -> tuple[bool, int]:
    """Evaluates whether an ISO 8601 start/end schedule window is currently active."""
    start_str = schedule_dict.get("start_time")
    end_str = schedule_dict.get("end_time")
    if not (start_str and end_str):
        return False, 0
    try:
        start_dt = _parse_iso_datetime(start_str)
        end_dt = _parse_iso_datetime(end_str)
        if start_dt <= now_utc < end_dt:
            rem = int((end_dt - now_utc).total_seconds())
            return True, rem
    except Exception as e:
        print(f"[state_machine] Schedule parsing error: {e}", file=sys.stderr)
    return False, 0


class ModeStateMachine:
    """Orchestrates system mode state and transitions."""

    def __init__(self, config: dict[str, Any], firewall: FirewallManager) -> None:
        self.config = config
        self.firewall = firewall
        self.current_mode: str = "Default"
        self.manual_override: str | None = None
        self._boot_monotonic = time.monotonic()
        self._manual_start_time: float | None = None
        self._manual_duration_sec: int | None = None

    def set_manual_mode(self, mode: str | None, duration_minutes: int | None = None) -> None:
        """Allows manual CLI triggers to override state."""
        self.manual_override = mode
        if mode == "Contest":
            self._manual_start_time = time.monotonic()
            self._manual_duration_sec = duration_minutes * 60 if duration_minutes else None
        else:
            self._manual_start_time = None
            self._manual_duration_sec = None

    def _eval_manual_override(self) -> tuple[str, int] | None:
        """Evaluates manual override mode and expiration."""
        if not self.manual_override:
            return None
        rem = 0
        is_manual_contest = (
            self.manual_override == "Contest"
            and self._manual_start_time
            and self._manual_duration_sec
        )
        if is_manual_contest:
            elapsed = int(time.monotonic() - self._manual_start_time)
            rem = max(0, self._manual_duration_sec - elapsed)
            if rem == 0 and self._manual_duration_sec > 0:
                print("[state_machine] Manual contest duration expired. Reverting to Default.")
                self.manual_override = None
                return "Default", 0
        return self.manual_override, rem

    def _eval_contest_triggers(self, now_utc: datetime) -> tuple[str, int] | None:
        """Checks auto-boot and scheduled triggers for Contest mode."""
        contest_cfg = self.config.get("contest", {})
        if contest_cfg.get("auto_start_on_boot"):
            dur_min = contest_cfg.get("duration_minutes", 300)
            elapsed = int(time.monotonic() - self._boot_monotonic)
            rem = max(0, (dur_min * 60) - elapsed)
            if rem > 0:
                return "Contest", rem

        active, rem = _is_schedule_active(contest_cfg.get("schedule", {}), now_utc)
        if active:
            return "Contest", rem
        return None

    def _eval_event_triggers(self, now_utc: datetime) -> tuple[str, int] | None:
        """Checks scheduled triggers for Event mode."""
        event_cfg = self.config.get("event", {})
        active, _ = _is_schedule_active(event_cfg.get("schedule", {}), now_utc)
        if active:
            return "Event", 0
        return None

    def evaluate_target_mode(self) -> tuple[str, int]:
        """Calculates the current target mode and remaining contest seconds."""
        if (manual_res := self._eval_manual_override()) is not None:
            return manual_res

        now_utc = datetime.now(timezone.utc)

        if (contest_res := self._eval_contest_triggers(now_utc)) is not None:
            return contest_res

        if (event_res := self._eval_event_triggers(now_utc)) is not None:
            return event_res

        return self.config.get("mode", "Default"), 0

    def _enter_contest_mode(self) -> None:
        """Applies all security and system lockdowns for Contest entry."""
        perform_clean_state_wipe()
        subprocess.run(["umount", "-l", "/media/event-data"], check=False)
        self.firewall.apply_mode_firewall("Contest", self.config)
        set_usb_storage_allowed(False)
        apply_browser_policy("Contest", self.config)
        update_wallpaper("Contest")
        send_desktop_notification(
            "Contest Mode Activated",
            "Strict Zero-Trust security engaged. USB locked.",
            urgency="critical",
        )

    def _exit_contest_mode(self, target_mode: str) -> None:
        """Restores network and unlocks USB storage when leaving Contest mode."""
        print(
            "[state_machine] Post-Contest transition: Unlocking USB storage and restoring network."
        )
        set_usb_storage_allowed(True)
        self.firewall.apply_mode_firewall(target_mode, self.config)
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)
        send_desktop_notification(
            "Contest Ended",
            "USB mass storage is now authorized. You may export your solutions.",
            urgency="normal",
        )

    def _switch_open_mode(self, target_mode: str) -> None:
        """Transitions between Default and Event modes."""
        self.firewall.apply_mode_firewall(target_mode, self.config)
        set_usb_storage_allowed(True)
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)

    def transition_to(self, target_mode: str, remaining_sec: int) -> None:
        """Performs state transition actions if mode changed."""
        if target_mode == self.current_mode:
            export_waybar_state(self.current_mode, remaining_sec)
            return

        old_mode = self.current_mode
        print(f"[state_machine] MODE TRANSITION: {old_mode} -> {target_mode}")
        self.current_mode = target_mode

        if target_mode == "Contest":
            self._enter_contest_mode()
        elif old_mode == "Contest" and target_mode in ("Default", "Event"):
            self._exit_contest_mode(target_mode)
        else:
            self._switch_open_mode(target_mode)

        export_waybar_state(self.current_mode, remaining_sec)
