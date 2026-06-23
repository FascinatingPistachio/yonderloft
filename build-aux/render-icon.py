#!/usr/bin/env python3
"""Render the app-icon PNGs from the SVG master with rsvg-convert.

flatpak build-export validates exported app icons in a sandbox without an SVG
loader, so the app icon ships as PNG; and Flathub wants a PNG anyway. This
rasterizes the single SVG master to the committed hicolor sizes so the PNGs and
the SVG never drift. Regenerate after editing the icon:

    python3 build-aux/render-icon.py

Requires rsvg-convert (librsvg). The build only installs the committed PNGs, so
this tool is dev-time only.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ID = "uk.aaronworld.Yonderloft"
SVG = os.path.join(ROOT, "data", "icons", f"{APP_ID}.svg")
ICONS_DIR = os.path.join(ROOT, "data", "icons")
SIZES = (48, 64, 128, 256)


def main() -> int:
    if shutil.which("rsvg-convert") is None:
        print("error: rsvg-convert not found (install librsvg2-tools / librsvg)",
              file=sys.stderr)
        return 1
    for px in SIZES:
        dest_dir = os.path.join(ICONS_DIR, f"{px}x{px}")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f"{APP_ID}.png")
        subprocess.run(
            ["rsvg-convert", "-w", str(px), "-h", str(px), SVG, "-o", dest],
            check=True,
        )
        print(f"wrote {os.path.relpath(dest, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
