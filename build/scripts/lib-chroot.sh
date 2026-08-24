#!/usr/bin/env bash
# Shared chroot setup helpers, sourced by 02-provision.sh / 03-optimize.sh.
# Not executable on its own.

chroot_mount() {
    local rootfs="$1"

    # Idempotent: 02-provision.sh and 03-optimize.sh both chroot into the
    # same rootfs within one container run (shared mount namespace, not
    # reset between stage scripts), so a second call must not re-mount
    # /proc or /sys — rootless Podman refuses a second sysfs instance even
    # via a fresh mountpoint ("sysfs already mounted on /sys").
    mountpoint -q "$rootfs/proc" || mount -t proc proc "$rootfs/proc"
    mountpoint -q "$rootfs/sys" || mount -t sysfs sysfs "$rootfs/sys"

    # A plain `mount --bind /dev $rootfs/dev` only captures /dev's own
    # (empty) tmpfs, not the individual per-device bind-mounts nested inside
    # it (rootless Podman's own /dev is itself a tree of devtmpfs sub-mounts
    # — one per device node — see `findmnt -R /dev`), leaving /dev/null etc.
    # missing and breaking apt-key/gpgv. `--rbind` (recursive) propagates
    # those nested mounts. Plain mknod doesn't work here either: even
    # --privileged rootless Podman denies CAP_MKNOD (verified directly).
    mountpoint -q "$rootfs/dev" || mount --rbind /dev "$rootfs/dev"

    cp /etc/resolv.conf "$rootfs/etc/resolv.conf"
}

chroot_umount() {
    local rootfs="$1"
    umount -lR "$rootfs/dev" 2>/dev/null || true
    umount -lf "$rootfs/proc" 2>/dev/null || true
    umount -lf "$rootfs/sys" 2>/dev/null || true
}
