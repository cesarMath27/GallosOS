# GallosOS Development Roadmap & Feature Tracker

This document translates the complete architectural and security specifications across all design documents (`ARCHITECTURE.md`, `CONFIG_SPEC.md`, `ANTI_CHEAT_AND_SECURITY.md`, `HARDWARE_COMPATIBILITY.md`, `COMPARATIVE_ANALYSIS.md`, and `PROVENANCE.md`) into a concrete, actionable engineering roadmap.

> **MVP Scope Definition:** The Minimum Viable Product (MVP) consists strictly of **Phase 1 through Phase 3**. Completing Phase 3 yields a fully functional, highly secure, drop-in replacement for HuronOS ready for local deployments. Phase 4 onwards represent polish, tooling, and post-GA telemetry.

---

## Phase 1: Bootstrapping, Casper & Core Filesystem Engine (Alpha)

*Goal: Build a containerized build pipeline producing a bootable Ubuntu 24.04 LTS Live ISO/USB supporting both UEFI SecureBoot and Legacy BIOS with Wayland.*

- [x] **OCI Build Container:** Create the `Containerfile` / `Dockerfile` (Podman/Docker) to bootstrap an `ubuntu:24.04` minimal rootfs without host pollution.
- [x] **Dual Bootloader Chain:** Configure hybrid bootloaders supporting:
  - UEFI Boot via GRUB (unsigned binary in initial walking skeleton; signed Canonical shim/GRUB chain in subsequent increment).
  - Legacy PC-BIOS (CSM) via `grub-pc` and MBR boot sector.
- [ ] **Casper Live Boot Engine:** *(Partial)* Configure `casper` boot parameters and hooks:
  - [x] Basic home seeding and overlay assembly hook (`vendor/inherited/maratona-casper/55gallos-live`).
  - [ ] Mount SquashFS modules (`.gsm`) into union layers using in-tree **OverlayFS**.
  - [ ] Automatically mount the 2-partition Live USB layout (`GALLOS_BOOT`, optional `event-data`) by filesystem label.
  - [ ] Support the `toram` boot parameter (copy entire OS to RAM).
  - [ ] Support `gallos.config=<path_or_url>` and Ventoy `/gallos/gallos.toml` detection.
- [x] **SquashFS Packaging Scripts:** Write `build-squashfs.sh` to package system layers with `mksquashfs -comp zstd`.
- [x] **Hybrid ISO Stitched Image:** Write `build-iso.sh` using `xorriso` / `grub-mkrescue` to generate hybrid bootable `.iso` images.
- [x] **Wayland Kiosk Desktop Shell:** Assemble the lightweight desktop environment:
  - `labwc` Wayland compositor configured with per-client security isolation.
  - `Waybar` status bar configured with an integrated dropdown application launcher, countdowns, network status, and layout switchers.

---

## Phase 2: Security Lockdown, Anti-Cheat Shield & Resource Hardening (Beta 1)

*Goal: Enforce strict Zero-Trust contest integrity, network air-gapping, and out-of-memory protections.*

- [x] **Anti-Cheat Enforcement (`nftables`):**
  - [x] Implement default DROP policy (Zero-Trust), IPv4-only (`table ip`)
  - [x] Disable IPv6 network-wide (kernel `ipv6.disable=1` + `/etc/sysctl.d/99-gallos-noipv6.conf`) — huronOS precedent, avoids a dual-stack firewall bypass
  - [x] Static IP / CIDR whitelisting for Judge Servers (`[security]` build-time posture; dynamic `gallos.toml` runtime rendering in Phase 3)
  - [x] Port-locking (block outbound 22, 853, and telemetry DNS list; STUN / hole-punching heuristics deferred to daemon phase)
- [x] **Peripheral & USB Lockdown:**
  - Deny USB mass-storage via modern `polkit`/`udisks2` JavaScript rules (`99-gallos-usb-block.rules` for the `contestant` user) with dynamic `udev` unbind rules (`99-contest-usb-block.rules`) as a fallback. Allow mice, keyboards, and HID in both cases.
- [x] **TTY & Privilege Hardening:**
  - Disable virtual terminal switching (TTY1–6) via `logind.conf.d/99-gallos-novt.conf`, masked `autovt@.service`, and kernel keymap remapping (`gallos-novt-keymap.service`).
  - Configure the `contestant` user as unprivileged without `sudo` (purged) or administrative rights, and locked `root` account.
- [x] **EarlyOOM Guard (`earlyoom -n` + `systembus-notify`):**
  - Configure `earlyoom -n` (D-Bus broadcast) and enable `earlyoom.service` (`systembus-notify` desktop bridge and `oom_score_adj` protection of `gallos-daemon`/browsers deferred to Phase 3 when those processes exist).

---

## Phase 3: Daemon, Mode State Machine & Dynamic Directives (Beta 2)

*Goal: Implement the real-time configuration engine, multi-mode scheduling, and network sync.*

- [x] **`gallos-daemon` Core Engine:**
  - Develop a persistent `systemd.service` (Python) capable of maintaining state and open sockets for real-time broadcasts.
  - Implement strict TOML parsing and schema validation against `schema/directives.schema.json` via `taplo`.
- [x] **Hybrid Config Ingestion & Fallback:**
  - Implement boot sequence logic: attempt to fetch remote `gallos.config_url` with a 5-second timeout; if unreachable, gracefully fall back to local `/boot/gallos/gallos.toml` cache with Plymouth/desktop warnings.
  - Support multi-profile selection via kernel boot arguments.
- [x] **3-Tier Precedence State Machine:**
  - Implement dynamic scheduling engine: $\text{Contest} \succ \text{Event} \succ \text{Default}$.
  - Transition wallpapers, network firewall rules, and application visibility automatically when contest time-windows start or expire.
- [x] **Dynamic Hot-Reload Hooks:**
  - Instantaneous wallpaper switching on mode transitions.
  - Dynamic `nftables` rule updates on the fly without rebooting.
- [x] **Post-Contest Workspace Support:**
  - Re-enable USB mass-storage drivers and provide visual prompts for manual code extraction.
- [x] **Machine Identity & Team Assignment:**
  - Assign workstation hostnames via DHCP MAC reservations or per-USB `machine.toml` directives.

---

## Phase 4: Specialized Contest Subsystems & Branding (Beta 3)

*Goal: Deliver printing, proctoring, white-labeling, and offline reference capabilities.*

- [ ] **`gallos-print` CUPS Subsystem:**
  - Develop the `gallos-print` CLI for contestants (`gallos-print solution.cpp`), inspecting and adapting the proven `printfile` (`a2ps` / `enscript`) pipeline pattern from `icpcsysops/ansible` and SWERC Lyon.
  - Support standard browser/judge GUI printing (`Ctrl + P` in Chromium / Firefox) through the default virtual CUPS queue.
  - Implement screenshot/window capture printouts via `grim` (`gallos-print --screenshot`).
  - Build `gallos-cups-filter` to inject syntax highlighting, line numbering, team metadata headers, timestamps, and page numbers.
  - Enforce printer whitelisting in `gallos.toml` to prevent unauthorized network print jobs.
- [ ] **Rapid White-Labeling & Branding Engine:**
  - Offline Plymouth boot splash generator from `boot_splash_logo_url`.
  - Custom CSS/GTK theme and wallpaper injector for Labwc and Waybar with optional `show_powered_by_gallos` watermark.
  - Custom GRUB boot menu background + colors (MVP: single-entry background/menu-color theming; a full `theme.txt` with per-entry icons is a later extension once multiple boot entries exist).
  - Ubuntu-branding removal pass (Plymouth splash, `/etc/os-release`/`lsb-release` `PRETTY_NAME`, pending trademark-policy verification) so the live OS reads as GallosOS rather than a visibly-reskinned Ubuntu.
  - Full design: [`docs/BOOT_BRANDING.md`](./docs/BOOT_BRANDING.md).
- [ ] **Keyboard Layout Switcher:**
  - Provision and expose Waybar switcher module for configured layouts (`latam`, `us`, `es`, etc.).
- [ ] **Offline Documentation & Translation:**
  - Bundle static HTML documentation packages (`cppreference-doc-en-html`, `python3-doc`, `openjdk-21-doc`).
  - Pre-configure browser bookmarks pointing to `file:///usr/share/doc/`.
  - Bundle lightweight offline dictionary (`GoldenDict` or `stardict`) with EN-ES / EN-PT databases to solve the translation firewall gap without bloating RAM.
- [ ] **`base_os` Version Flexibility (`build.toml`):**
  - Formalize the maintainer-tested-default vs. community-supported `base_os` tiers in the build pipeline (`ubuntu-22.04-minimal`, `ubuntu-26.04-minimal`, interim non-LTS releases) per `docs/ARCHITECTURE.md` §3.1.
  - Document the `kernel` (HWE) pairing needed when targeting newer hardware than an older `base_os` release ships by default.
- [ ] **Proprietary GPU Driver Support (`drivers/nvidia-proprietary`):**
  - Package the opt-in NVIDIA proprietary driver as a DKMS-carrying `.gsm` module per `docs/ARCHITECTURE.md` §4.
  - Implement the MOK signing-key generation/persistence step in `gallos-builder` (`docs/BUILD_SYSTEM.md` §4) and document the one-time per-machine `mokutil --import` venue-setup flow (`docs/HARDWARE_COMPATIBILITY.md` §1.3).
  - **Future dependency:** a `langs/programming/cuda-toolkit` module (nvcc, cuDNN) for CUDA programming sessions depends on this driver work landing first — not scoped or specified yet.

---

## Phase 5: Organizer Tooling Suite (RC 1)

*Goal: Build standalone utilities for mass USB preparation, migration, and visual configuration.*

- [ ] **`gallos-convert` (HuronOS Migration CLI):**
  - Parser for legacy `.hdf` configuration formats into canonical `gallos.toml`.
  - Include `--validate` (taplo schema check) and `--diff` CLI flags.
- [ ] **`gallos-flash` (Mass Multi-USB Flashing Tool):**
  - Multi-threaded parallel writer supporting 50+ simultaneous USB targets.
  - Native support for Linux, macOS, and Windows WSL2 via `usbipd-win`.
  - Automatic creation of a FAT32 `GALLOS_BOOT` partition plus an ext4 `event-data` partition sized to consume all remaining drive capacity. No `contest-data` partition — `Contest` mode never persists to the boot drive (see `docs/ARCHITECTURE.md` §4, item 5).
  - Automated per-USB injection of unique `machine.toml` credentials.
- [ ] **GallosOS Config Builder (Web & GUI App):**
  - Interactive web application (Angular) hosted on GitHub Pages or locally.
  - Visual time-picker for contest schedule, checkbox module selector, firewall IP list builder, and live TOML preview/download.

---

## Phase 6: Software Toolchains, Virtual Appliances & CI/CD (GA Release)

*Goal: Package contest programming languages, IDEs, VM targets, and automated build pipelines.*

- [ ] **Compilers & Runtimes:**
  - Package and verify standard contest toolchains (cross-referencing package manifests from `icpc-environment/icpc-env`, `maratona-linux/maratona-team-tools`, and `ioi-2025/contestant-vm`): GCC (C/C++), Clang, OpenJDK 21 (Java), Python 3, PyPy3, Rust, Kotlin, Mono / .NET.
- [ ] **Contestant IDEs:**
  - Pre-configure and package VSCodium (with offline extensions), JetBrains Community Edition (IntelliJ IDEA, PyCharm), CLion (with activation script), Code::Blocks, Geany, Kdevelop, Neovim (lazyvim), Vim (linters, plugins), and Kate.
- [ ] **Anti-Cheat Purge & Telemetry Neutralization (Post-MVP):**
  - Write a startup service to purge `com.intellij.ml.llm` and Copilot plugins from JetBrains and VSCodium installations.
  - Neutralize telemetry and crash reporting in Chromium, Firefox, and VSCodium.
- [ ] **Virtual Machine Appliances:**
  - Automated building of `.ova` (VirtualBox / VMware) and `.qcow2` (KVM/QEMU) appliances.
  - Pre-configure guest additions and display resizing for virtualization.
- [ ] **Public Documentation Site:**
  - Deploy an official Docusaurus or GitBook site for user-facing documentation, quickstarts, and architectural deep-dives.
- [ ] **CI/CD & Release Automation:**
  - GitHub Actions workflow to build release ISOs inside OCI containers on Git tags.
  - Automated smoke tests in headless QEMU to verify boot, firewall default-DROP, and daemon operation.

---

## Phase 7: Venue Controller & Advanced Telemetry (Post-GA / v2.0)

*Goal: Centralized infrastructure for massive deployments, fleet monitoring, and automated auditing.*

- [ ] **Venue Controller Server Mode:**
  - Dedicated GallosOS boot mode to act as the central orchestrator (DHCP, NTP, MAC mapping).
- [ ] **Administrative Proctoring, Auditing & Keystroke Forensics:**
  - Adopt/fork the **`martkeys`** daemon architecture (`icpcsysops/ansible`) for kernel-level `/dev/input/event*` keystroke and mouse activity aggregation (Wayland compositor-agnostic) when `enable_keystroke_forensics = true`.
  - Implement scheduled background screenshot captures via dedicated root Wayland socket.
  - Bundle `node-exporter` and `gallos-exporter` for real-time fleet health metrics.
  - Build `gallos-audit-export` CLI to aggregate and export ephemeral workstation logs, EarlyOOM kill events, firewall drops, `martkeys` activity metrics, print history, and proctoring snapshots into a persistent `gallos-audit-YYYYMMDD.tar.gz` archive.
