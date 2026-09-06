#!/usr/bin/env python3
"""Syntax checks for the Wayland kiosk desktop overlay (build/desktop/).

Run by scripts/check.sh and .github/workflows/ci.yml. Verifies that:
  - labwc XML files (rc.xml, menu.xml) are well-formed XML
  - the Waybar config (JSONC: JSON plus // comments) parses as JSON
  - every keybind in rc.xml executes only a helper that exists in the
    overlay (or an allow-listed compositor-side program), so a typo in a
    binding never ships as a dead key
  - every helper script under usr/bin is executable and starts with a
    Bash/sh shebang (in-band tooling rule, AGENTS.md)
Exit status 1 on the first category of failure found.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parsing our own tracked files
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DESKTOP = REPO_ROOT / "build" / "desktop"
LABWC = DESKTOP / "etc" / "xdg" / "labwc"
WAYBAR_CONFIG = DESKTOP / "etc" / "xdg" / "waybar" / "config.jsonc"
BIN_DIR = DESKTOP / "usr" / "bin"

# Programs a keybind / menu entry may Execute without shipping in build/desktop.
EXTERNAL_ALLOWED = {"foot", "footclient", "wmenu", "swaybg", "mako", "waybar"}


def strip_jsonc_comments(text: str) -> str:
    """Removes // line comments that are not inside a JSON string."""
    out_lines = []
    for line in text.splitlines():
        in_string = False
        escaped = False
        cut = None
        for i, ch in enumerate(line):
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_string:
                escaped = True
            elif ch == '"':
                in_string = not in_string
            elif ch == "/" and not in_string and line[i : i + 2] == "//":
                cut = i
                break
        out_lines.append(line if cut is None else line[:cut])
    return "\n".join(out_lines)


def check_xml() -> list[str]:
    errors = []
    for name in ("rc.xml", "menu.xml"):
        path = LABWC / name
        try:
            ET.parse(path)  # noqa: S314 - trusted, repository-tracked file
        except (ET.ParseError, OSError) as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
    return errors


def check_waybar() -> list[str]:
    try:
        json.loads(strip_jsonc_comments(WAYBAR_CONFIG.read_text(encoding="utf-8")))
    except (ValueError, OSError) as exc:
        return [f"{WAYBAR_CONFIG.relative_to(REPO_ROOT)}: {exc}"]
    return []


def _execute_commands(path: Path) -> list[str]:
    root = ET.parse(path).getroot()  # noqa: S314
    commands = []
    for action in root.iter("action"):
        if action.get("name") == "Execute":
            cmd = action.get("command") or (action.findtext("command") or "")
            commands.append(cmd.strip())
    return commands


def check_keybind_targets() -> list[str]:
    errors = []
    shipped = {p.name for p in BIN_DIR.iterdir()} if BIN_DIR.is_dir() else set()
    for name in ("rc.xml", "menu.xml"):
        for cmd in _execute_commands(LABWC / name):
            program = cmd.split()[0] if cmd else ""
            if program not in shipped and program not in EXTERNAL_ALLOWED:
                errors.append(f"{name}: Execute target '{program}' is not shipped in build/desktop")
    return errors


def check_helpers() -> list[str]:
    errors = []
    shebang = re.compile(r"^#!\s*/(usr/)?bin/(env\s+)?(bash|sh)\b")
    for script in sorted(BIN_DIR.iterdir()):
        rel = script.relative_to(REPO_ROOT)
        if not os.access(script, os.X_OK):
            errors.append(f"{rel}: not executable")
        first = script.open(encoding="utf-8").readline()
        if not shebang.match(first):
            errors.append(f"{rel}: must start with a bash/sh shebang (in-band tooling rule)")
    return errors


def main() -> int:
    checks = (
        ("labwc XML", check_xml),
        ("Waybar JSONC", check_waybar),
        ("keybind targets", check_keybind_targets),
        ("helper scripts", check_helpers),
    )
    failed = False
    for label, fn in checks:
        errors = fn()
        if errors:
            failed = True
            print(f"[validate_desktop] {label}: FAILED", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"[validate_desktop] {label}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
