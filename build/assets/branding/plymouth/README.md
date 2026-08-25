# Plymouth Theme Source

Not populated yet — see [`docs/BOOT_BRANDING.md`](../../../../docs/BOOT_BRANDING.md) § "1. Plymouth theme" for the full design.

When implemented (Phase 4), this folder will hold the source for a custom `script`-plugin Plymouth theme named `gallos`:

| File | Purpose |
| :--- | :--- |
| `gallos.plymouth` | Theme descriptor (`[Plymouth Theme]` ini section: `Name`, `ModuleName=script`, `ScriptFile=/usr/share/plymouth/themes/gallos/gallos.script`). |
| `gallos.script` | The Plymouth script itself: solid `#1e1e2e` background, centered logo, pulsing-dots progress indicator. |
| `logo-placeholder.png` | Fallback logo used when an organizer's `gallos.toml` doesn't set `[branding].boot_splash_logo_url`. Exact provenance (hand-authored vs. programmatically generated, matching the flat-color PNG pattern already used for desktop wallpapers in `build/scripts/02-provision.sh`) is an open decision — see the spec's "Open questions" section. |

`build/scripts/02-provision.sh` (Stage 2) will `cp` these into `$ROOTFS/usr/share/plymouth/themes/gallos/`, run `plymouth-set-default-theme -R gallos`, and — critically — call `update-initramfs -u` *after* that so the theme is actually baked into the initrd `build-squashfs.sh` later copies out verbatim.

Recommended background dimensions: none fixed yet — Plymouth's `script` plugin queries the framebuffer resolution at runtime and scripts should position elements relative to `Window.GetWidth()`/`Window.GetHeight()`, not hardcoded pixel coordinates.
