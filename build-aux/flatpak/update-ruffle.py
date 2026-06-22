#!/usr/bin/env python3
"""Pin the bundled Ruffle release in the Flatpak manifest.

Queries the latest ruffle-rs/ruffle release, finds the *web-selfhosted* zip,
downloads it to compute its sha256, and rewrites the ``ruffle`` module's source
URL + sha256 in the Flatpak manifest. Run this whenever you want to bump Ruffle:

    python3 build-aux/flatpak/update-ruffle.py

Pass ``--tag nightly-2026-06-01`` to pin a specific release instead of latest.
Pure stdlib (urllib/json/hashlib), so it runs anywhere Python does.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request

API_LATEST = "https://api.github.com/repos/ruffle-rs/ruffle/releases/latest"
API_BY_TAG = "https://api.github.com/repos/ruffle-rs/ruffle/releases/tags/{tag}"
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "uk.aaronworld.Yonderloft.json")
ASSET_SUFFIX = "web-selfhosted.zip"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "yonderloft-ruffle-updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _find_asset(release: dict) -> tuple[str, str]:
    for asset in release.get("assets", []):
        if asset["name"].endswith(ASSET_SUFFIX):
            return release["tag_name"], asset["browser_download_url"]
    raise SystemExit(f"No '*{ASSET_SUFFIX}' asset in release {release.get('tag_name')!r}")


def _sha256(url: str) -> str:
    digest = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "yonderloft-ruffle-updater"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        for chunk in iter(lambda: resp.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="pin a specific release tag instead of latest")
    args = ap.parse_args()

    release = _get_json(API_BY_TAG.format(tag=args.tag) if args.tag else API_LATEST)
    tag, url = _find_asset(release)
    print(f"Ruffle release: {tag}\n  {url}")
    print("Downloading to compute sha256 …")
    sha = _sha256(url)
    print(f"  sha256 = {sha}")

    with open(MANIFEST, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    for module in manifest["modules"]:
        if module.get("name") == "ruffle":
            source = module["sources"][0]
            source["url"] = url
            source["sha256"] = sha
            break
    else:
        raise SystemExit("No 'ruffle' module found in manifest")

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print(f"Updated {os.path.relpath(MANIFEST)} → Ruffle {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
