# Upstream: maratona-linux/maratona-usuario-icpc

- **Repository:** <https://github.com/maratona-linux/maratona-usuario-icpc>
- **License:** GPL-2.0+ (see `LICENSE` in this directory, copied verbatim from upstream)
- **Reference upstream tree:** `maratona-linux/maratona-usuario-icpc` (local reference checkout)

## What's vendored here

- `99-gallos-usb-block.rules` — adapted from upstream's `polkit-1/icpc-udisks.pkla`.
  Upstream used PolicyKit's legacy `.pkla` (localauthority) file format to deny
  all `org.freedesktop.udisks2.*` operations for the unprivileged contest user (`icpc`).
  Because Ubuntu 24.04 LTS (`noble`) ships a modern `polkitd` that dropped the legacy
  `.pkla` backend entirely in favor of JavaScript rule files in `/etc/polkit-1/rules.d/`,
  this file translates upstream's deny-by-identity-and-action-prefix logic into modern
  polkit JavaScript (`polkit.addRule`) targeting the `contestant` user.

Tracked in `docs/PROVENANCE.md`'s ledger under "USB Storage Lockdown via polkit/udisks2".
