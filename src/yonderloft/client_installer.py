"""Pure (GTK-free) helpers for the ``client`` runtime's fetch/update logic.

The networking, download and process launch live in ``client.py``; this module
holds only the parts that can be unit-tested without GTK: turning a GitHub
release page URL into an API endpoint, picking the Linux AppImage asset from a
release, and comparing versions to decide whether to update.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlsplit


def github_api_latest(source_url: str) -> Optional[str]:
    """Map a github.com repo/releases URL to its 'latest release' API endpoint.

    Returns None for non-GitHub URLs (caller falls back to opening the page).
    """
    parts = urlsplit(source_url)
    if parts.netloc.lower() not in ("github.com", "www.github.com"):
        return None
    segments = [s for s in parts.path.split("/") if s]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"


def pick_appimage(release: dict) -> Optional[dict]:
    """Choose the AppImage asset from a GitHub release JSON.

    Prefers x86_64 builds when several AppImages are present. Returns
    ``{"version", "url", "name", "size"}`` or None.
    """
    appimages = [
        a for a in release.get("assets", [])
        if str(a.get("name", "")).lower().endswith(".appimage")
    ]
    if not appimages:
        return None

    def rank(asset):
        name = asset["name"].lower()
        # Prefer 64-bit desktop builds; deprioritise arm/i386.
        return (
            0 if ("x86_64" in name or "amd64" in name or
                  not any(arch in name for arch in ("arm", "aarch", "i386", "i686")))
            else 1
        )

    best = sorted(appimages, key=rank)[0]
    return {
        "version": release.get("tag_name", ""),
        "url": best["browser_download_url"],
        "name": best["name"],
        "size": int(best.get("size", 0)),
    }


def normalize_version(version: Optional[str]) -> tuple[int, ...]:
    """Turn a tag like 'v1.4.5' into (1, 4, 5) for comparison. '' → (0,)."""
    nums = re.findall(r"\d+", version or "")
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(remote: Optional[str], local: Optional[str]) -> bool:
    """True if the remote version tag is newer than the locally installed one."""
    if not local:
        return True
    return normalize_version(remote) > normalize_version(local)
