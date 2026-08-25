# Development, Linting & Testing (`gallos-daemon`)

This document covers the local development workflow for the Python code in this repository — currently `gallos-daemon` (`daemon/`), the early Phase 3 runtime configuration daemon. It does **not** cover the containerized ISO build pipeline (`build/scripts/*.sh`, `build.toml`) beyond the ShellCheck step those scripts share with this same quality gate — see [`docs/BUILD_SYSTEM.md`](./BUILD_SYSTEM.md) for everything else about that pipeline.

---

## 1. Prerequisites

| Tool | Required? | Purpose |
| :--- | :--- | :--- |
| Python `>= 3.10` | Yes | Matches `requires-python` in `pyproject.toml`. |
| [`ruff`](https://docs.astral.sh/ruff/) | Yes | Linting (style, complexity, security via `bandit`-equivalent rules) and formatting. |
| [`pytest`](https://docs.pytest.org/) | Yes | Runs the `daemon/tests/` unit test suite. |
| [`shellcheck`](https://www.shellcheck.net/) | Optional locally | Lints `build/scripts/*.sh`. `scripts/check.sh` skips this step with a warning if `shellcheck` isn't on `PATH`, but it is required in CI and via the pre-commit hook. |
| [`taplo`](https://taplo.tamasfe.dev/) | Optional locally | Validates TOML files against `schema/directives.schema.json`. If absent, `scripts/check.sh` falls back to `scripts/validate_toml.py`, which only checks TOML *syntax*, not schema conformance. |
| [`pre-commit`](https://pre-commit.com/) | Optional | Runs a subset of these checks automatically on every `git commit`. |

Install the Python tools with `pip install ruff pytest` (matching what `.github/workflows/ci.yml` installs in CI).

---

## 2. Repository layout: `daemon/`

```text
daemon/
├── src/
│   ├── __init__.py       # Package marker, __version__
│   ├── main.py           # Entry point: daemon loop, Unix-socket IPC dispatch (START/STOP/STATUS/RELOAD)
│   ├── config.py         # Hybrid config ingestion: remote gallos.toml fetch (5s timeout) with local fallback
│   ├── state_machine.py  # 3-tier mode state machine (Contest > Event > Default), schedule evaluation, Clean State Wipe
│   ├── firewall.py       # Dynamic nftables ruleset generation and periodic DNS re-resolution
│   ├── browser_policy.py # Chromium/Firefox enterprise managed-policy JSON generation
│   ├── identity.py       # MAC-address-to-machine.toml identity resolution, hostname assignment
│   ├── desktop.py        # Wallpaper (swaybg), notifications (Mako), Waybar status export
│   └── usb_manager.py    # USB mass-storage lockdown (Polkit rule + udev fallback)
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_state_machine.py
    ├── test_firewall.py
    ├── test_browser_policy.py
    ├── test_identity.py
    ├── test_daemon_ipc.py    # Unix-socket IPC dispatch (main.py's GallosDaemon)
    └── test_usb_manager.py
```

Each `daemon/tests/test_*.py` file mirrors the `daemon/src/*.py` module it exercises (`test_daemon_ipc.py` covers `main.py`'s IPC dispatcher). `desktop.py` currently has no dedicated test file. When adding a function to a module, add or extend the matching test file rather than creating a new one.

---

## 3. One command: `./scripts/check.sh`

`scripts/check.sh` is the single pre-flight command — run it before proposing any change as complete. It runs, in order, and reports a pass/fail summary at the end:

1. **Ruff lint** — `ruff check .`
2. **Ruff format check** — `ruff format --check .`
3. **Pytest** — `python3 -m pytest daemon/tests/ -v`
4. **ShellCheck** — `shellcheck build/scripts/*.sh` (skipped with a warning if `shellcheck` isn't installed)
5. **TOML validation** — `taplo check` if `taplo` is installed (schema-aware), else `python3 scripts/validate_toml.py` (syntax-only fallback covering `pyproject.toml`, `.taplo.toml`, `examples/*.toml`, `build/profiles/*.toml`)

```sh
./scripts/check.sh
```

---

## 4. Individual commands

For iterating on a single module without re-running the whole suite:

```sh
# Lint / auto-fix
ruff check .
ruff check . --fix

# Format / format-check
ruff format .
ruff format --check .

# Run all daemon tests, or a single file
python3 -m pytest daemon/tests/ -v
python3 -m pytest daemon/tests/test_state_machine.py -v

# Shell scripts
shellcheck build/scripts/*.sh
shellcheck -x build/scripts/*.sh   # also follow `# shellcheck source=` into lib-mirrors.sh / lib-chroot.sh

# TOML syntax only (fallback validator)
python3 scripts/validate_toml.py
```

---

## 5. Pre-commit hooks

Install the hooks once per clone:

```sh
pip install pre-commit
pre-commit install
```

`.pre-commit-config.yaml` then runs automatically on every `git commit`:

- `ruff` (with `--fix`) and `ruff-format`
- `shellcheck`, scoped to `build/scripts/*.sh`
- Standard `pre-commit-hooks`: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files`

This does not run `pytest` — the test suite is intentionally left to `./scripts/check.sh` and CI, since running the full suite on every commit slows down the local git workflow.

---

## 6. Continuous Integration (GitHub Actions)

`.github/workflows/ci.yml` defines a `GallosOS CI` workflow, job `lint-and-test`, triggered on every `push` and `pull_request` targeting `main`. It runs on `ubuntu-24.04` with Python 3.12 and executes:

1. `ruff check .`
2. `ruff format --check .`
3. `pytest daemon/tests/ -v`
4. ShellCheck via `ludeeus/action-shellcheck@master`, scanning `build/scripts`
5. TOML syntax validation — an inline Python step using `tomllib`, globbing `**/*.toml` **recursively across the entire repository**

**Note the TOML-check asymmetry:** CI's step 5 checks every `*.toml` file in the repo, while the local fallback (`scripts/validate_toml.py`, used by `./scripts/check.sh` when `taplo` isn't installed) only checks `pyproject.toml`, `.taplo.toml`, `examples/*.toml`, and `build/profiles/*.toml`. A TOML file outside those patterns can pass locally and still be caught by CI. Also, neither CI nor `pytest` checks the JSON *schema* conformance of `examples/*.toml` / `gallos.toml` against `schema/directives.schema.json` — that's still `taplo`-only (local CLI or the VS Code `tamasfe.even-better-toml` extension).

This CI workflow covers code quality (`daemon/`, `build/scripts/*.sh`, TOML syntax) — it does not build or boot the ISO itself; that remains a manual process (see [`docs/BUILD_SYSTEM.md`](./BUILD_SYSTEM.md)).

---

## 7. Centralized tool configuration (`pyproject.toml`)

All Ruff and Pytest configuration lives in `pyproject.toml`, not in ad hoc CLI flags:

- `[tool.ruff]` / `[tool.ruff.lint]`: rule sets `E`, `W`, `F`, `I`, `B`, `C90`, `UP`, `PLR0912`, `PLR0915`, `S`; `line-length = 100`; `target-version = "py310"`.
- `[tool.ruff.lint.mccabe]` / `[tool.ruff.lint.pylint]`: complexity ceilings — `max-complexity = 10`, `max-branches = 12`, `max-statements = 40`.
- `[tool.ruff.lint.per-file-ignores]`: `daemon/tests/**` is allowed `assert` (`S101`), predictable temp paths (`S108`), and longer test functions (`PLR0915`).
- `[tool.pytest.ini_options]`: `testpaths = ["daemon/tests"]`, `python_files = ["test_*.py"]`, `addopts = "-v --strict-markers"`.

Changing a lint rule or complexity threshold means editing `pyproject.toml`, not any individual script.

---

## 8. Editor integration (VS Code)

`.vscode/settings.json` wires up:

- `charliermarsh.ruff` as the default Python formatter, with format-on-save and `source.fixAll.ruff` / `source.organizeImports.ruff` on save.
- `python.testing.pytestEnabled: true` with `pytestArgs: ["daemon/tests"]`, so the Testing sidebar discovers and runs the suite directly.
- `tamasfe.even-better-toml` (recommended in `.vscode/extensions.json`) for live TOML schema validation against `schema/directives.schema.json` while editing `gallos.toml` / `examples/*.toml`.
