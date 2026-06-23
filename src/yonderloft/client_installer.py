"""Pure (GTK-free) helpers for the ``client`` runtime's fetch/update logic.

The networking, download and process launch live in ``runtimes/client.py``; this
module holds only the parts that can be unit-tested without GTK: turning a GitHub
release page URL into an API endpoint, picking the best runnable Linux asset
(AppImage or portable tarball) from a release, locating the launch binary inside
an extracted tarball, and comparing versions.
"""
from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlsplit

# Portable-tarball extensions we can extract and run.
_TARBALL_EXTS = (".tar.xz", ".tar.gz", ".tgz", ".tar.bz2")

# Names/extensions in an extracted client tree that are never the entry point.
_NOT_ENTRY_NAMES = {
    "chrome-sandbox", "chrome_crashpad_handler", "crashpad_handler",
    "apprun", "apprun.wrapped",
}
_NOT_ENTRY_EXTS = (
    ".so", ".dll", ".dylib", ".pak", ".dat", ".bin", ".json", ".html", ".htm",
    ".txt", ".md", ".node", ".png", ".svg", ".ico", ".desktop", ".yml", ".yaml",
    ".css", ".js", ".map",
)


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


def _is_linux_tarball(name: str) -> bool:
    low = name.lower()
    if not low.endswith(_TARBALL_EXTS):
        return False
    # Skip obvious Windows/macOS/other-arch tarballs.
    if any(bad in low for bad in ("win", "mac", "darwin", "osx", "arm", "aarch")):
        return False
    return True


def asset_kind(name: str) -> Optional[str]:
    """'appimage', 'tarball', or None for a release-asset filename."""
    low = name.lower()
    if low.endswith(".appimage"):
        return "appimage"
    if _is_linux_tarball(name):
        return "tarball"
    return None


def pick_asset(release: dict) -> Optional[dict]:
    """Choose the best runnable Linux asset from a GitHub release JSON.

    Prefers an AppImage (self-contained), else a portable Linux tarball. Returns
    ``{"version", "url", "name", "size", "kind"}`` or None.
    """
    candidates = []
    for a in release.get("assets", []):
        kind = asset_kind(str(a.get("name", "")))
        if kind:
            candidates.append((a, kind))
    if not candidates:
        return None

    def rank(item):
        asset, kind = item
        name = asset["name"].lower()
        kind_rank = 0 if kind == "appimage" else 1
        arch_rank = 0 if ("x86_64" in name or "amd64" in name or "x64" in name
                          or not any(a in name for a in ("i386", "i686"))) else 1
        return (kind_rank, arch_rank)

    best, kind = sorted(candidates, key=rank)[0]
    return {
        "version": release.get("tag_name", ""),
        "url": best["browser_download_url"],
        "name": best["name"],
        "size": int(best.get("size", 0)),
        "kind": kind,
    }


def find_launch_target(root: str, hint: str = "") -> Optional[str]:
    """Find the app's launch binary inside an extracted client tree.

    Heuristic: among executable regular files that aren't known helpers
    (chrome-sandbox, crash handlers) or data/libraries, prefer one whose name
    matches ``hint``, then the shallowest, then the shortest name.
    """
    hint_tokens = [t for t in re.split(r"[^a-z0-9]+", hint.lower()) if len(t) > 2]
    candidates: list[tuple[int, int, int, str]] = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            low = name.lower()
            if low in _NOT_ENTRY_NAMES or low.endswith(_NOT_ENTRY_EXTS):
                continue
            path = os.path.join(dirpath, name)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                continue
            depth = os.path.relpath(path, root).count(os.sep)
            matches_hint = 0 if any(t in low for t in hint_tokens) else 1
            candidates.append((matches_hint, depth, len(name), path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][3]


def normalize_version(version: Optional[str]) -> tuple[int, ...]:
    """Turn a tag like 'v1.4.5' into (1, 4, 5) for comparison. '' → (0,)."""
    nums = re.findall(r"\d+", version or "")
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(remote: Optional[str], local: Optional[str]) -> bool:
    """True if the remote version tag is newer than the locally installed one."""
    if not local:
        return True
    return normalize_version(remote) > normalize_version(local)
