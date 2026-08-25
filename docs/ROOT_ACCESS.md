# Root Recovery Access — Design

**Status:** Implemented (`recovery.root_password_hash` in `gallos.toml`, applied by `gallos-daemon` at every boot/reload via `daemon/src/root_access.py`).

## Context

`build/scripts/03-harden.sh` (Stage 3, the "Contestant privilege hardening" step, lines 263–273) currently does this inside the chroot:

```bash
rm -f /usr/bin/sudo /usr/bin/sudoedit /usr/sbin/visudo
rm -rf /etc/sudoers /etc/sudoers.d
passwd -l root || true
```

`sudo`'s binaries and config are deleted outright, and `passwd -l root` locks the root account's password hash. This is `docs/ANTI_CHEAT_AND_SECURITY.md` § 9.1 ("Privileged Command & Sudo Revocation") in code form, and it's the implementation behind `ROADMAP.md`'s Phase 2 "TTY & Privilege Hardening" item (line 42), which is already checked off (`[x]`).

**Why this matters for the design below:** adding any form of root access back is not a neutral feature addition — it is a deliberate, partial reversal of a shipped anti-cheat control. It should be scoped as narrowly as the actual need requires, not as broadly as would be convenient.

### Correcting the huronOS comparison

The motivating idea was "huronOS allows declaring a root password, GallosOS should too." That's true but the framing doesn't hold up as feature parity: huronOS never had a locked-root posture to begin with. Per `HuronOS/website/docs/usage/root-access.md`, huronOS's root account **always** has a password (default `toor` if the organizer doesn't change it), set via an `install.sh --root-password` **installer flag** — not a `.hdf` directives-file config (directives govern wallpaper, firewall, software modules, etc.; root password is architecturally a different, install-time-only mechanism in huronOS's own vocabulary). There is no huronOS equivalent of GallosOS's locked-root/purged-sudo stance to toggle away from. So this design isn't "catching up to huronOS" — it's GallosOS choosing to reopen a control it already has that huronOS never had.

## The actual need

An organizer needs to fix something on a specific workstation during a live event (misbehaving driver, a config file, a stuck service) without re-flashing the USB. This is a real, recurring operational need in contest venues.

## Scope, as confirmed with the maintainer

- **Local only, no network component.** The mechanism is: open the `foot` terminal already available inside the kiosk Wayland session (`Super+Return`, per `docs/WAYLAND_DESKTOP.md`), then `su root` with a password, from the physical machine.
- **No SSH.** SSH is explicitly out of scope for this pass — see "Explicitly out of scope" below. It doesn't get built now, doesn't get a firewall exception now, nothing.
- **Contest-mode gating is an open question**, deliberately left undecided here — see "Open question" below.

## Design: local-only root password

### Where the password lives

Two candidate locations, with a recommendation:

| Option | How it'd work | Trade-off |
| :--- | :--- | :--- |
| `build.toml` (build-time) | A new field read by `03-harden.sh`, baked in once via `chpasswd` instead of `passwd -l root`. Static for the life of that ISO build. | Simple, but static — can't be rotated without rebuilding, and can't be mode-gated at all without separate logic added to the daemon anyway. |
| `gallos.toml` (runtime) — **recommended** | A new field, applied/removed dynamically by `gallos-daemon`'s `state_machine.py`, the same way it already reacts to mode transitions for the firewall (`firewall.py`) and USB lockdown (`usb_manager.py`). | Reuses existing mode-reactive infrastructure — once Contest-gating is decided, it's one more `if mode == Contest` branch in code that already has that shape, not a new subsystem. |

**Recommendation: `gallos.toml`, applied dynamically by the daemon**, specifically because it makes the still-open Contest-gating decision (below) a small follow-up change instead of a redesign.

### Secret-handling risk — must be addressed before implementation

`gallos.toml` can be fetched from a remote URL (`daemon/src/config.py`'s hybrid ingestion — a Gist, a campus server, a VPS; see `README.md`'s own suggested "host a single canonical `gallos.toml`... on a GitHub Gist" workflow). A plaintext root password in that file would travel over HTTP(S) on every fetch and could end up sitting in a semi-public Gist right alongside contest schedule/firewall config.

Two mitigations to carry into implementation, not treated as optional polish:

1. **Never store the plaintext password.** Store a `crypt`-format hash (the same format `/etc/shadow` uses), the same way any Linux password field should be stored. The daemon writes the hash directly into `/etc/shadow` (or calls `chpasswd -e`) rather than ever holding a plaintext value beyond the moment the organizer typed it into their own `gallos.toml`.
2. **Consider restricting this field to the local baked-in fallback config only**, never the remote-fetched one — structurally the same restriction `docs/CONFIG_SPEC.md` already applies to `[branding].boot_splash_logo_url` (see its "Architectural Caveat (Boot Splash)" note), just for a different reason: that field is baked-in-only because there's no network at boot; this one would be baked-in-only to avoid a secret transiting and resting in a possibly-shared remote config file at all.

## Contest-mode gating — resolved: Option B (always available)

The root password, when configured, is available in every mode, including an active Contest window — there is no mode-gating logic in `state_machine.py`. This was a deliberate maintainer choice to cover mid-contest emergency fixes, accepting that the "judge-only network" guarantee during Contest is no longer literally airtight from a local-privilege-escalation standpoint (a locally-escalated root process isn't a network path in itself, but it can rewrite the firewall rules the Contest lockdown depends on). Option A (blocked during Contest) was the more conservative alternative considered and rejected — see git history on this document for the original open-question framing if the trade-off needs revisiting.

## Explicitly out of scope (this pass)

- **SSH entirely.** `openssh-server` isn't installed anywhere in the pipeline today, and port 22 is hard-dropped by both firewalls (`build/scripts/03-harden.sh` and `daemon/src/firewall.py` line 146), named as an "evasion tunnel" alongside WireGuard/Tor/SOCKS5 in `docs/ANTI_CHEAT_AND_SECURITY.md` line 19. None of that changes here.
- **Venue Controller-driven remote access.** `docs/ARCHITECTURE.md` line 580 ("Optional Ansible Fleet Orchestration Bridge") already documents the intended shape of this for Tier 3: the Venue Controller drives Ansible over SSH to contestant machines for diagnostics/recovery at scale. When that phase is built, remote root-recovery access should follow that already-endorsed pattern — **SSH key-based auth only, reachable solely from the Venue Controller's IP**, not a password, and not reachable from the wider LAN. This document's local-`su`-with-password mechanism is a stopgap for venues that don't have (or haven't yet reached) a Venue Controller, not a substitute for that design.
- **A related doc inconsistency worth flagging, not fixing here:** `docs/ARCHITECTURE.md` line 623 currently states "All GallosOS USBs flashed from the same ISO image are identical — same SHA256, same root credentials, same SSH host keys," which assumes root credentials and SSH host keys exist on every image. That's not true of the current implementation (root locked, no sshd). Whoever implements either this document or the Venue Controller SSH bridge should reconcile that line with whatever actually ships.
- **`contestant` user's own credentials.** `contestant` has no password today (`useradd -m -s /bin/bash contestant` with no `passwd`/`chpasswd` call — pure TTY autologin per `build/scripts/02-provision.sh`). Nothing here changes that; the `su root` step happens from inside the already-logged-in kiosk session, not via a fresh login.

## References

- `docs/ANTI_CHEAT_AND_SECURITY.md` § 9.1 — the control this document proposes partially reopening.
- `build/scripts/03-harden.sh` lines 263–273 — current implementation (`passwd -l root`, sudo purge).
- `daemon/src/firewall.py` line 146 — dynamic firewall's port-22 drop rule.
- `docs/ARCHITECTURE.md` § 11.1 (lines 617–623) and line 580 — the Venue Controller SSH/Ansible pattern this design deliberately defers to, and the credentials-assumption inconsistency to reconcile later.
- `ROADMAP.md` line 42 — Phase 2 "TTY & Privilege Hardening," already shipped, which this document proposes partially revisiting.
- `HuronOS/website/docs/usage/root-access.md` — source of the corrected huronOS comparison above.
- `docs/CONFIG_SPEC.md` — "Architectural Caveat (Boot Splash)," the existing precedent for a baked-in-only config field, referenced above as a possible model for handling the password field's exposure risk.
