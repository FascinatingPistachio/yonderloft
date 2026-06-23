#!/usr/bin/env python3
"""Render the dormer-window app icon to PNGs from the same geometry as the SVG.

AppStream's `appstreamcli compose` (run by flatpak-builder) needs a readable
raster icon; a scalable SVG alone trips `file-read-error` in some build images,
and Flathub wants a PNG anyway. This produces committed PNGs at the hicolor
sizes; the build just installs them. Regenerate after editing the icon:

    python3 build-aux/render-icon.py

Pure Pillow. Geometry mirrors data/icons/uk.aaronworld.Yonderloft.svg
(128px viewBox), scaled to each target size.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "icons")
SIZES = (128, 256)

DUSK = (36, 31, 49, 255)        # #241F31
SILL = (58, 51, 73, 255)        # #3A3349
LIP = (27, 23, 38, 255)         # #1B1726
GLOW_TOP = (255, 209, 92, 255)  # #FFD15C
GLOW_BOT = (229, 165, 10, 255)  # #E5A50A


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def _vgradient(size, top, bottom):
    grad = Image.new("RGBA", (1, size))
    for y in range(size):
        grad.putpixel((0, y), _lerp(top, bottom, y / max(1, size - 1)))
    return grad.resize((size, size))


def render(px: int) -> Image.Image:
    s = px / 128.0  # SVG viewBox is 128
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def rect(x, y, w, h, r, fill):
        d.rounded_rectangle([x * s, y * s, (x + w) * s, (y + h) * s],
                            radius=max(0, r * s), fill=fill)

    # Dusk frame.
    rect(22, 20, 84, 92, 10, DUSK)

    # Lit window with the amber glow (vertical gradient, clipped to a rounded rect).
    wx, wy, ww, wh, wr = 34, 32, 60, 68, 5
    win_box = [round(wx * s), round(wy * s), round((wx + ww) * s), round((wy + wh) * s)]
    win_w, win_h = win_box[2] - win_box[0], win_box[3] - win_box[1]
    grad = _vgradient(max(win_w, win_h), GLOW_TOP, GLOW_BOT).resize((win_w, win_h))
    mask = Image.new("L", (win_w, win_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, win_w - 1, win_h - 1],
                                           radius=wr * s, fill=255)
    img.paste(grad, (win_box[0], win_box[1]), mask)

    # Muntins (window bars).
    rect(61, 32, 6, 68, 0, DUSK)
    rect(34, 63, 60, 6, 0, DUSK)

    # Sill with darker front lip for Adwaita depth.
    rect(20, 100, 88, 10, 3, SILL)
    rect(20, 106, 88, 6, 3, LIP)
    return img


def main() -> int:
    for px in SIZES:
        dest_dir = os.path.join(OUT_DIR, f"{px}x{px}")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "uk.aaronworld.Yonderloft.png")
        render(px).save(dest)
        print(f"wrote {os.path.relpath(dest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
