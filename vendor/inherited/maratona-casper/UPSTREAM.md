# Upstream: maratona-linux/maratona-casper

- **Repository:** https://github.com/maratona-linux/maratona-casper
- **License:** GPL-2.0 (see `LICENSE` in this directory, copied verbatim from upstream)
- **Reference commit:** `bdd6b117f3c734d192225446520bcba459d3d33b` (2018-10-29)

## What's vendored here

- `55gallos-live` — adapted from upstream's `55maratona-fixes` casper-bottom
  hook. See the header comment in that file for exactly what was kept
  (the hook shape, home-directory seeding pattern) versus what was dropped
  (the `/proc/cmdline` factoryreset/mlinstall/mlshell branching, which was
  specific to maratona-linux's install-media workflow and has no GallosOS
  equivalent yet).
- `casper-gsm-overlay.sh` and `casper-gsm-overlay.insert.sh` — **not**
  derived from upstream maratona-casper; these are GallosOS-original,
  applied by `build/scripts/02-provision.sh` as a build-time patch to the
  Ubuntu `casper` *package's* own `scripts/casper` (initramfs-tools), to
  mount `.gsm` SquashFS software modules into the OverlayFS union. See the
  header comment in `casper-gsm-overlay.sh` for why this has to be a
  build-time patch rather than another casper-bottom hook.

Tracked in `docs/PROVENANCE.md`'s ledger under "Casper Live Boot Hooks".
