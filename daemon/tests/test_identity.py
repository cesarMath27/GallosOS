"""Unit tests for gallos-daemon workstation identity module."""

from daemon.src.identity import _find_matched_machine, _resolve_hostname


def test_resolve_hostname_direct():
    machine = {"pc_name": "lab-pc42"}
    assert _resolve_hostname(machine) == "lab-pc42"


def test_resolve_hostname_room_and_number():
    machine = {"room": "lab-a", "pc_number": "15"}
    assert _resolve_hostname(machine) == "lab-a-pc15"


def test_find_matched_machine_from_config():
    config = {
        "machines": [
            {"mac": "aa:bb:cc:dd:ee:ff", "pc_name": "pc-01", "team_name": "Los Gallos"},
            {"mac": "11:22:33:44:55:66", "pc_name": "pc-02", "team_name": "Team 2"},
        ]
    }
    matched = _find_matched_machine(config, {}, ["aa:bb:cc:dd:ee:ff"])
    assert matched is not None
    assert matched["pc_name"] == "pc-01"
    assert matched["team_name"] == "Los Gallos"
