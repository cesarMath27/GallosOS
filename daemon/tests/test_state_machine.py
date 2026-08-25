"""Unit tests for gallos-daemon 3-tier mode state machine."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from daemon.src.state_machine import ModeStateMachine


def test_state_machine_default_fallback():
    mock_firewall = MagicMock()
    config = {"mode": "Default"}
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Default"
    assert rem == 0


def test_state_machine_manual_override():
    mock_firewall = MagicMock()
    config = {"mode": "Default"}
    sm = ModeStateMachine(config, mock_firewall)
    sm.set_manual_mode("Contest", duration_minutes=60)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 3500 <= rem <= 3600

    sm.set_manual_mode("Default")
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Default"
    assert rem == 0


def test_state_machine_auto_start_on_boot():
    mock_firewall = MagicMock()
    config = {"mode": "Default", "contest": {"auto_start_on_boot": True, "duration_minutes": 10}}
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 590 <= rem <= 600


def test_state_machine_wall_clock_schedule():
    mock_firewall = MagicMock()
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(minutes=10)
    end_utc = now_utc + timedelta(minutes=50)

    config = {
        "mode": "Default",
        "contest": {
            "schedule": {"start_time": start_utc.isoformat(), "end_time": end_utc.isoformat()}
        },
    }
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 2900 <= rem <= 3000
