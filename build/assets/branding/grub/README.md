# GRUB Boot Menu Background

Not populated yet — see [`docs/BOOT_BRANDING.md`](../../../../docs/BOOT_BRANDING.md) § "2. GRUB theme" for the full design.

When implemented (Phase 4, MVP scope), this folder will hold:

| File | Purpose |
| :--- | :--- |
| `background.png` | Full-screen background for the GRUB menu, same dark navy (`#1e1e2e`) palette as the Plymouth splash and desktop wallpaper. |

`build/scripts/build-iso.sh` (Stage 5b) will `cp` this into `$STAGING/boot/grub/background.png` before calling `grub-mkrescue`, and the `grub.cfg` heredoc in that same script will gain `insmod gfxterm`, `insmod png`, `background_image /boot/grub/background.png`, and `menu_color_normal`/`menu_color_highlight` directives.

**Explicitly out of scope for the MVP pass:** a full `theme.txt`-based GRUB theme with per-entry selection icons. `build-iso.sh` generates a single boot menu entry today ("GallosOS Live"); icon-per-entry only becomes useful once there are multiple entries (safe-mode, memtest, etc.). The spec documents this as a clean upgrade seam, not something to build now.
