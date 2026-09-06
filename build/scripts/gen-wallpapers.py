#!/usr/bin/env python3
"""Generate the GallosOS desktop wallpapers (Stage 2 of the build pipeline).

Pure-stdlib (zlib/struct) PNG writer, so the build container needs no image
library and no binary asset is committed to git. Produces one image per
mode (docs/CONFIG_SPEC.md § Mode Semantics: Default / Event / Contest
branding), all on the same "Graphite & Steel" graphite gradient with a soft
mode-coloured glow — blue (Default), teal (Event), red (Contest).

    gen-wallpapers.py OUTPUT_DIR [--width 1920 --height 1080]
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

# Base gradient (top -> bottom) shared by every mode.
GRADIENT_TOP = (0x1A, 0x1F, 0x27)
GRADIENT_BOTTOM = (0x0F, 0x12, 0x16)

# Mode accent glows: (r, g, b, peak_alpha). Kept muted so the desktop stays
# formal and text on top of it (notifications, terminals) remains legible.
MODE_GLOWS = {
    "default": (0x5A, 0x9B, 0xD8, 0.30),
    "event": (0x3A, 0xA3, 0x9A, 0.30),
    "contest": (0xD1, 0x49, 0x5B, 0.34),
}


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _lerp(a: int, b: int, t: float) -> float:
    return a + (b - a) * t


def render(width: int, height: int, glow: tuple[int, int, int, float]) -> bytes:
    """Returns the raw (filter byte + RGB) scanlines for one wallpaper."""
    gr, gg, gb, peak = glow
    # Glow centre sits high on the left third; radius spans most of the screen.
    cx, cy = width * 0.32, height * 0.28
    radius_sq = (height * 0.95) ** 2
    dx_sq = [(x - cx) ** 2 for x in range(width)]

    rows = bytearray()
    for y in range(height):
        t = y / max(height - 1, 1)
        base_r = _lerp(GRADIENT_TOP[0], GRADIENT_BOTTOM[0], t)
        base_g = _lerp(GRADIENT_TOP[1], GRADIENT_BOTTOM[1], t)
        base_b = _lerp(GRADIENT_TOP[2], GRADIENT_BOTTOM[2], t)
        dy_sq = (y - cy) ** 2
        row = bytearray([0])  # PNG filter type 0 (None)
        for x in range(width):
            d = (dx_sq[x] + dy_sq) / radius_sq
            if d >= 1.0:
                row += bytes((int(base_r), int(base_g), int(base_b)))
                continue
            a = peak * (1.0 - d) ** 2
            row += bytes(
                (
                    int(base_r + (gr - base_r) * a),
                    int(base_g + (gg - base_g) * a),
                    int(base_b + (gb - base_b) * a),
                )
            )
        rows += row
    return bytes(rows)


def write_png(path: Path, width: int, height: int, raw_rows: bytes) -> None:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    with path.open("wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_png_chunk(b"IHDR", ihdr))
        f.write(_png_chunk(b"IDAT", zlib.compress(raw_rows, 9)))
        f.write(_png_chunk(b"IEND", b""))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for mode, glow in MODE_GLOWS.items():
        target = args.output_dir / f"{mode}.png"
        write_png(target, args.width, args.height, render(args.width, args.height, glow))
        print(f"[gen-wallpapers] wrote {target} ({args.width}x{args.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
