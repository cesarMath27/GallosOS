# Branding Assets (`build/assets/branding/`)

This directory holds the static, build-time source assets for GallosOS's boot-time branding — the Plymouth boot splash and the GRUB boot menu background. Both are consumed by the containerized build pipeline (`build/scripts/`) and baked directly into the ISO; neither can be updated remotely at runtime (see `docs/CONFIG_SPEC.md` § "Architectural Caveat (Boot Splash)").

**Status: scaffolding only.** This folder is a placeholder ahead of ROADMAP Phase 4 ("Specialized Contest Subsystems & Branding"). No build script currently reads from it. The full design — what goes in each subfolder, how the pipeline consumes it, and open decisions still to make — is written up in [`docs/BOOT_BRANDING.md`](../../../docs/BOOT_BRANDING.md). Read that before implementing Phase 4's branding engine.

## Layout

```text
build/assets/branding/
├── plymouth/   # Plymouth "script" theme source (gallos.plymouth, gallos.script, default logo)
└── grub/       # GRUB boot menu background image and (later) a full theme.txt
```

See each subfolder's `README.md` for format/resolution expectations and which pipeline stage consumes it.
