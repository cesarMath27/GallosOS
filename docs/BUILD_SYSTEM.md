# Containerized Build Pipeline (`build.toml`)

GallosOS is designed to be **100% reproducible and infrastructure-agnostic**. To achieve this, the entire ISO generation process is isolated inside a **Podman/Docker Container Build System** (`gallos-builder`).

This approach completely eliminates host OS pollution and allows developers to build GallosOS on Linux, macOS, or Windows (via WSL2) without installing tools like `debootstrap`, `mksquashfs`, or `xorriso` on their local machines.

---

## 1. The Holy Trinity of GallosOS Configurations

GallosOS separates concerns across three distinct TOML configuration files:

| Config File | Phase | Description | Web UI? |
| :--- | :--- | :--- | :--- |
| **`build.toml`** | **Build-Time** | Used by the `gallos-builder` container to generate a custom ISO (strip blobs, inject apt packages). | ❌ No |
| **`gallos.toml`** | **Run-Time** | The global contest rules, branding, and mode logic (`Contest`/`Event`/`Default`). | ✅ **Yes (Config Builder)** |
| **`machine.toml`** | **Run-Time** | The physical identity of the specific workstation (Seat ID, Static IP). | ❌ No (Local Script) |

---

## 2. Declarative ISO Generation (`build.toml`)

Rather than maintaining fragile Bash scripts with hardcoded `apt-get` commands, organizers feed a `build.toml` manifest into the container pipeline. This defines exactly what gets baked into the immutable `rootfs.squashfs` before the ISO is stitched together.

### Example `build.toml` Blueprint

```toml
[build]
base_os = "ubuntu-24.04-minimal"
kernel = "linux-generic-hwe-24.04"
target_arch = "amd64"
bootstrap_method = "debootstrap"  # or "tarball" — see § 2.2
apt_mirror = "auto"               # or an explicit mirror URL — see § 2.2

[optimization]
# Strip down the OS to save RAM and USB space for Tier 0 (low-resource) environments
strip_man_pages = true
strip_docs = true
remove_apt_cache = true
locales = ["en_US.UTF-8", "es_MX.UTF-8"]

[packages]
# Base packages permanently baked into the rootfs (No .gsm required)
preinstall_apt = [
    "curl",
    "git",
    "python3-pip",
    "valgrind",
    "gdb"
]

[modules]
# Which GallosOS Software Modules (.gsm) to pre-bundle into the final ISO's /gallos/software/ directory
bundle = [
    "langs/gcc",
    "langs/openjdk",
    "programming/vscodium",
    "programming/vim",
    "tools/foot"
]
```

### 2.1 `base_os` Version Tiers

`base_os` is not hardcoded to `ubuntu-24.04-minimal` — it is the pipeline's default and the only version the upstream GallosOS maintainer builds and tests against. See `docs/ARCHITECTURE.md` § 3.1 for the full maintainer-tested-vs-community-supported tier table (`ubuntu-22.04-minimal`, `ubuntu-26.04-minimal`, and interim non-LTS releases are architecturally supported but not upstream-validated). Pair a non-default `base_os` with a matching `kernel = "linux-generic-hwe-<version>"` when targeting newer hardware than the chosen release ships by default.

### 2.2 `bootstrap_method` and `apt_mirror` (Stage 1 source)

`bootstrap_method` picks how Stage 1 builds the base rootfs:

- **`"debootstrap"` (default):** runs `debootstrap` live inside the container against `apt_mirror`. This is the default specifically because mirror flexibility genuinely exists at this layer — Canonical's apt archive is broadly mirrored (see `launchpad.net/ubuntu/+cdmirrors` for the official list) and the same mirror choice also serves Stage 2's package installs, since `debootstrap` configures the target's `sources.list` to match.
- **`"tarball"`:** imports Canonical's official `ubuntu-base-<version>-base-amd64.tar.gz` snapshot (published at `cdimage.ubuntu.com/ubuntu-base/releases/`) from `.cache/base-images/`, verified against its `SHA256SUMS`/`SHA256SUMS.gpg`. This tarball is itself Canonical's own `debootstrap` output, republished as a pinned artifact — useful for fully offline builds or maximum build-to-build reproducibility (a fixed snapshot rather than whatever the mirror serves today). Its tradeoff: unlike the apt archive, this tarball is **effectively single-source** — checked during this pipeline's development, a real community mirror that does carry Ubuntu's `ubuntu-releases` (full ISO) tree returned 404 for the `ubuntu-base` tree, so no broad mirror network exists for it. No official BitTorrent distribution exists for it either (`cdimage.ubuntu.com/ubuntu-base/` has no `.torrent` files — only the full Desktop/Server ISOs at `releases.ubuntu.com` get those).

`apt_mirror` controls which apt mirror `debootstrap` (and Stage 2's `apt-get`) use:

- **`"auto"` (default):** tries an ordered fallback list of independently-verified mirrors (`build/scripts/lib-mirrors.sh`), first reachable one wins.
- **An explicit URL** (e.g. `"http://us.archive.ubuntu.com/ubuntu/"`): pins one mirror. If it's unreachable the build fails with a clear error rather than silently substituting another — an organizer who names a specific mirror (e.g. an internal proxy) should get a clear signal, not a silent swap.

`debootstrap`'s own default only writes a bare `main`-component, no-pockets `sources.list` line — no `restricted`/`universe`/`multiverse`, and no `-updates`/`-backports`/`-security`. The pipeline overwrites it after bootstrapping with all four components across `$SUITE`, `$SUITE-updates`, and `$SUITE-backports` on the chosen `apt_mirror`, plus `$SUITE-security` pinned to `security.ubuntu.com` specifically (not the general mirror — community mirrors don't reliably mirror the security pocket promptly; this matches Canonical's own convention).

---

## 3. The 4-Stage Container Pipeline (`Makefile` / `Containerfile`)

When a developer runs `make iso CONFIG=profiles/build-icpc.toml`, the container executes the following stages internally:

### Stage 1: Base Bootstrap (`debootstrap` or `ubuntu-base` tarball)

Controlled by `build.toml`'s `bootstrap_method` (§ 2.2). By default the container runs `debootstrap` against `apt_mirror` (`"auto"` picks the first reachable mirror from an ordered fallback list — `build/scripts/lib-mirrors.sh`). Setting `bootstrap_method = "tarball"` instead imports Canonical's official `ubuntu-base-<version>-base-amd64.tar.gz` rootfs snapshot from `.cache/base-images/`, verified against its `SHA256SUMS`/`SHA256SUMS.gpg` before extraction — useful for offline builds or maximum reproducibility, at the cost of that artifact being effectively single-source (§ 2.2 has the details). Either path establishes the basic directory structure and populates `/dev`, `/proc`, and `/sys` for chrooting.

### Stage 2: Provisioning (`chroot`)

The builder enters the chroot environment and:

1. Installs the Wayland Kiosk core (`labwc`, `waybar`, `foot`).
2. Injects the `gallos-daemon` core service and configuration engine (Python).
3. Parses `build.toml` $\to$ `[packages]` and executes `apt-get install -y <packages>`.

### Stage 3: Stripping & Optimization

To keep the Live OS memory footprint minimal (Crucial for `toram` boot):

1. Parses `build.toml` $\to$ `[optimization]`.
2. Deletes unused locales via `locale-gen`.
3. Purges `/usr/share/doc`, `/usr/share/man`, and `/var/cache/apt/archives`.

### Stage 4: Squash & Stitch (`mksquashfs` & `xorriso`)

1. Compresses the entire optimized rootfs into `filesystem.squashfs` (using `zstd` for high-speed decompression in RAM).
2. Sets up the GRUB bootloader for both UEFI SecureBoot (`shim`) and Legacy BIOS (`grub-pc`).

---

## 3.1 Shell Script Validation

The pipeline's orchestration scripts (`build/scripts/*.sh`) are expected to pass [`shellcheck`](https://www.shellcheck.net/) before merge — run `shellcheck build/scripts/*.sh` locally, or `shellcheck -x build/scripts/*.sh` to also follow the `# shellcheck source=` directives already in `01-bootstrap.sh`, `02-provision.sh`, and `03-optimize.sh` into their sourced libs (`lib-mirrors.sh`, `lib-chroot.sh`). No CI currently enforces this automatically; treat it as a pre-merge check until a pipeline is wired up.

---

## 4. MOK Signing Key Persistence (Optional Proprietary Kernel Modules)

The `drivers/nvidia-proprietary` `.gsm` module (see `docs/HARDWARE_COMPATIBILITY.md` § 1.3) carries a DKMS-built, out-of-tree kernel module, which requires a Machine Owner Key (MOK) signature to load under SecureBoot. Because organizers enroll that MOK **once per physical machine** (a venue-setup step, not a per-boot one), the signing key itself must stay stable across ISO rebuilds — a rotated key would silently invalidate every previously-enrolled machine's trust.

- `gallos-builder` generates the MOK signing keypair once (outside of any single `make iso` invocation) and persists it as a pipeline secret, reusing it to sign the `nvidia-dkms` module on every subsequent build.
- Each release ships the corresponding public certificate alongside the ISO so organizers can run `mokutil --import` during venue setup.
- This key is independent of, and unrelated to, Canonical's `shim`/kernel signing keys described in `docs/HARDWARE_COMPATIBILITY.md` § 1.2 — those cover the stock boot chain; the MOK covers only the opt-in proprietary module.
3. Copies the `.gsm` files declared in `[modules]` into the ISO layout.
4. Uses `xorriso` to output the final hybrid, bootable image: `gallosOS-custom-amd64.iso`.
