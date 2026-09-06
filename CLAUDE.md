# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status: MVP (Phase 1–3) implemented, organizer tooling not started

GallosOS is a Linux Live distribution for competitive-programming contests (ICPC, IOI, OMI, Maratona SBC), designed as a modern replacement for huronOS. Per `ROADMAP.md`, Phases 1–3 (the MVP: containerized Live ISO build pipeline, the `gallos-daemon` runtime configuration daemon, and the Wayland kiosk desktop shell) are implemented — `daemon/` has full unit-test coverage under `daemon/tests/` (run in CI) `build/desktop/` holds the Wayland kiosk shell (labwc/Waybar/foot/mako dotfiles plus the Bash `gallos-*` contest hotkey toolkit — `gallos-run` compile-and-run, `gallos-hotkeys` cheat sheet, whitelisted `gallos-menu` — see `docs/WAYLAND_DESKTOP.md` and `build/desktop/README.md`; the desktop shell has not been QEMU-boot-verified yet), and `build/` is a working containerized pipeline that has produced a bootable ICPC-profile ISO with the Casper Live Boot Engine fully implemented: `.gsm`/OverlayFS module mounting, GALLOS_BOOT config exposure, `event-data` label-mounting, `toram`, and `gallos.config=`/Ventoy `gallos.toml` detection are all QEMU-boot-verified (`build/scripts/test-iso-qemu.sh`) — see `ROADMAP.md` Phase 1's "Known issues" note for a few adjacent `gallos-daemon` bugs this verification pass found and mostly fixed (one, event-data's mount-namespace visibility, is still open). In-tree organizer tools (`tools/` — `gallos-flash`, `gallos-inject`, `gallos-convert`, `gallos-config-builder`, Phase 5) have not been started; the `tools/` directory does not exist yet. Do not claim features exist before their respective phase or write about GallosOS as if it has been hardware-tested (QEMU/KVM boot-testing is not hardware validation) — see the non-negotiable rules below.

A GitHub Actions CI workflow (`.github/workflows/ci.yml`) now runs on every push/PR to `main`, automatically enforcing: Ruff linting and formatting (`ruff check .`, `ruff format --check .`), the `daemon/tests/` `pytest` suite, `shellcheck` against `build/scripts/*.sh` and the `build/desktop/` helper scripts, `scripts/validate_desktop.py` (labwc XML, Waybar JSONC, keybind targets), and TOML syntax validation (recursively, via `tomllib`). The same checks run locally in one shot via `./scripts/check.sh`, and `.pre-commit-config.yaml` runs Ruff and ShellCheck automatically on every local commit (`pre-commit install` once to enable it) — see `docs/DEVELOPMENT.md` for the full breakdown. TOML *schema* validation against `schema/directives.schema.json` (as opposed to plain syntax) is still a manual/editor-only check, wired up via `.taplo.toml` and VS Code's `tamasfe.even-better-toml` extension (`taplo lint`/`taplo check` if the CLI is available) — CI only checks TOML syntax, not schema conformance. This CI covers code quality only (`daemon/`, `build/scripts/*.sh`, `build/desktop/`, TOML syntax); there is still no CI that builds or boots the ISO itself — that remains a manual process, see `docs/BUILD_SYSTEM.md`.

## Non-negotiable rules (from AGENTS.md — read it in full before substantial work)

- **English only.** All docs, comments, schema descriptions, and commit messages.
- **Zero hallucination.** Every package name, version, compiler flag, or claim must be grounded in local reference trees (see below) or real upstream sources. Never fabricate links or use placeholder domains.
- **Never claim empirical validation.** No implying hardware benchmarks, write-speed tests, or lab trials have occurred — GallosOS is architectural/conceptual only right now. Frame comparisons as derived from binary/source inspection.
- **Cross-document coherence.** Terminology, directory layouts, and mode-precedence rules must stay synchronized across `README.md`, `ROADMAP.md`, `docs/`, `examples/`, and `schema/`. A change to one often requires updating the others.
- **Canonical terms** (defined in `README.md` § Terminology): **Contestant** (never "participant" as primary), **Organizer**, **Venue Controller** (optional, Tier 3 only — never assume it exists), **Judge Server** (external, e.g. BOCA/DOMjudge/CMS/omegaUp — GallosOS never hosts it).
- **In-band vs out-of-band tooling split:** anything running inside the live contest OS (`gallos-daemon`, hooks) must be Bash/Python for field-hackability without a compiler; anything the organizer runs on their own host (`gallos-flash`, `gallos-convert`) must be a statically compiled Rust binary.
- **Infrastructure-agnostic.** Never assume a Venue Controller, internet connectivity, or specific network services are present — GallosOS spans a 5-tier spectrum from fully air-gapped to institutionally managed.

## Repository layout

```text
GallosOS/
├── AGENTS.md                  # Full agent/contributor ruleset — canonical source of the rules above
├── README.md                  # Project overview, MVP scope, terminology, key pillars
├── ROADMAP.md                 # Phase 1–7 engineering checklist (Alpha → GA → post-GA)
├── docs/
│   ├── ARCHITECTURE.md        # OverlayFS/SquashFS layering, Wayland kiosk, build & VM testing
│   ├── CONFIG_SPEC.md         # gallos.toml directive spec, Config Builder, mode hierarchy, .hdf migration
│   ├── BUILD_SYSTEM.md        # build.toml spec, the 5-stage containerized build pipeline
│   ├── WAYLAND_DESKTOP.md     # Labwc/Waybar/Foot/Mako desktop spec, keybindings
│   ├── HARDWARE_COMPATIBILITY.md
│   ├── ANTI_CHEAT_AND_SECURITY.md  # nftables threat model, USB lock, telemetry stripping
│   ├── COMPARATIVE_ANALYSIS.md     # GallosOS vs HuronOS vs Maratona vs ICPC-Env vs IOI-VM
│   └── PROVENANCE.md          # Third-party vendoring ledger, license tracking
├── examples/*.toml            # Production-ready gallos.toml profiles per contest archetype (see examples/README.md)
└── schema/directives.schema.json  # JSON Schema (draft-07) validating gallos.toml
```

`HuronOS/`, `maratona-linux/`, `icpc-env/`, `contestant-vm/`, and `ansible/` are present on disk but **gitignored** — they are local upstream reference trees kept only for cross-referencing real package names/versions/patterns when writing specs. Never edit them, and never assume they exist in a checkout other than this one.

## Core architectural concepts

**The three-file config split** (see `docs/BUILD_SYSTEM.md` § "Holy Trinity"):

- `build.toml` — build-time only, feeds the (planned) `gallos-builder` container to produce a custom ISO.
- `gallos.toml` — run-time global contest policy (identical across all workstations): schedule windows, judge whitelist, allowed software, printing mode, branding.
- `machine.toml` — run-time per-workstation identity: hostname, room, team, seat label.

`examples/*.toml` are templates to be copied to `gallos.toml`, not consumed directly.

**Mode hierarchy** (strict precedence, defined in `docs/CONFIG_SPEC.md`):
`Contest ≻ Event ≻ Default`. Contest = strict lockdown/judge-only network/fresh isolation. Event = training-camp mode with persistent workspace, hidden the instant a Contest window starts. Default = fallback when no window is active. Any feature touching scheduling, firewall rules, or desktop state must respect this precedence.

**Storage model:** immutable read-only base SquashFS + modular `.gsm` software packages, unioned via OverlayFS with an ephemeral `tmpfs` upper layer — the machine returns to a pristine state on reboot. Contestants export code manually to USB at contest end.

**Unified monorepo strategy** (`AGENTS.md` § Unified Monorepo Architecture & Component Map): this repo holds the core build pipeline, daemon, docs, configs, and all organizer tools (`tools/gallos-flash`, `tools/gallos-inject`, `tools/gallos-convert`, `tools/gallos-config-builder`).

## Working on docs and examples

- When adding/editing an `examples/*.toml` profile, keep the `#:schema` header pointing at `schema/directives.schema.json` and validate structurally against it (see `software_list` pattern `^(internet|langs|programming|tools|docs)/[a-z0-9_+-]+$`, `iso8601_datetime` format, etc.).
- Schema changes in `schema/directives.schema.json` must be reflected in `docs/CONFIG_SPEC.md` and, if directive names change, in every `examples/*.toml`.
- New roadmap items belong in the correct `ROADMAP.md` phase (Phase 1–3 = MVP; Phase 4+ is explicitly post-MVP polish) — don't scope-creep the MVP phases.
