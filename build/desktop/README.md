# `build/desktop/` — Wayland kiosk desktop overlay

Everything in this directory mirrors the target filesystem layout of the live
image and is copied verbatim into the root filesystem by Stage 2 of the build
pipeline (`build/scripts/02-provision.sh`, `cp -a build/desktop/. "$ROOTFS"/`).
It is the single source of truth for the contestant desktop described in
[`docs/WAYLAND_DESKTOP.md`](../../docs/WAYLAND_DESKTOP.md).

| Path | Role |
| :--- | :--- |
| `etc/xdg/labwc/rc.xml` | labwc compositor config: keybindings, workspaces, snap regions, window rules. |
| `etc/xdg/labwc/menu.xml` | Desktop right-click menu (whitelisted launchers only). |
| `etc/xdg/labwc/themerc-override` | Window decoration, menu and OSD colours ("Graphite & Steel"). |
| `etc/xdg/labwc/autostart` | Session start-up: wallpaper watcher, mako, Waybar, `foot --server`. |
| `etc/xdg/labwc/environment` | Toolkit environment (Wayland backends, cursor theme). |
| `etc/xdg/waybar/config.jsonc`, `style.css` | Status bar layout and GTK CSS theme. |
| `etc/xdg/foot/foot.ini` | Terminal font, palette, cursor, scrollback. |
| `etc/xdg/mako/config` | Notification appearance and urgency behaviour. |
| `etc/profile.d/gallos-kiosk.sh` | Kiosk session launcher on tty1 (keyboard layouts, session bus, `labwc -C /etc/xdg/labwc`). |
| `usr/bin/gallos-*` | In-band helper scripts (Bash only — AGENTS.md § In-Band vs Out-of-Band tooling): `gallos-run`, `gallos-menu`, `gallos-launch`, `gallos-hotkeys`, `gallos-power`, `gallos-terminal`, `gallos-wmenu`, `gallos-waybar-status`, `gallos-wallpaper`. |
| `usr/share/gallos/apps.list` | Whitelisted application catalogue for `gallos-menu`. |

Wallpapers are not stored here: `build/scripts/gen-wallpapers.py` generates
`/usr/share/backgrounds/gallos/{default,event,contest}.png` at build time.

Checks: `./scripts/check.sh` runs ShellCheck over every script here and
`scripts/validate_desktop.py` (well-formed labwc XML, parseable Waybar JSONC,
every keybind/menu `Execute` target shipped, Bash shebangs). Targeted
versions: labwc 0.7.1, Waybar 0.9.24, foot 1.16.2, wmenu 0.1.6, mako — the
Ubuntu 24.04 LTS packages pinned by `build/profiles/icpc.toml`.

The three desktop-facing tables must stay in sync whenever a binding changes:
`etc/xdg/labwc/rc.xml`, `usr/bin/gallos-hotkeys` (on-screen cheat sheet) and
`docs/WAYLAND_DESKTOP.md` §4.
