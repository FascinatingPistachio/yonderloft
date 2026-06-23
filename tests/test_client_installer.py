"""Tests for the GTK-free client install/update helpers."""
from __future__ import annotations

import pytest

from yonderloft import client_installer as ci


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/nhaar/Waddle-Forever/releases",
     "https://api.github.com/repos/nhaar/Waddle-Forever/releases/latest"),
    ("https://github.com/owner/repo.git",
     "https://api.github.com/repos/owner/repo/releases/latest"),
    ("https://github.com/owner/repo/releases/tag/v1",
     "https://api.github.com/repos/owner/repo/releases/latest"),
])
def test_github_api_latest(url, expected):
    assert ci.github_api_latest(url) == expected


@pytest.mark.parametrize("url", [
    "https://gitlab.com/owner/repo",
    "https://example.com/downloads",
    "https://github.com/owner",  # no repo
])
def test_github_api_latest_rejects(url):
    assert ci.github_api_latest(url) is None


def _release():
    # Mirrors the real Waddle Forever v1.4.5 asset list.
    return {
        "tag_name": "v1.4.5",
        "assets": [
            {"name": "default.zip", "browser_download_url": "https://x/default.zip", "size": 1},
            {"name": "WaddleForever-Setup-1.4.5.exe", "browser_download_url": "https://x/s.exe", "size": 2},
            {"name": "WaddleForever-1.4.5.dmg", "browser_download_url": "https://x/a.dmg", "size": 3},
            {"name": "WaddleForeverClient-1.4.5.AppImage",
             "browser_download_url": "https://x/c.AppImage", "size": 111},
        ],
    }


def test_pick_appimage_finds_the_appimage():
    asset = ci.pick_appimage(_release())
    assert asset["version"] == "v1.4.5"
    assert asset["url"].endswith("c.AppImage")
    assert asset["size"] == 111


def test_pick_appimage_none_when_absent():
    assert ci.pick_appimage({"tag_name": "v1", "assets": [
        {"name": "win.exe", "browser_download_url": "u"}]}) is None


def test_pick_appimage_prefers_x86_64():
    release = {"tag_name": "v2", "assets": [
        {"name": "App-arm64.AppImage", "browser_download_url": "https://x/arm", "size": 1},
        {"name": "App-x86_64.AppImage", "browser_download_url": "https://x/amd", "size": 1},
    ]}
    assert ci.pick_appimage(release)["url"].endswith("amd")


@pytest.mark.parametrize("v,expected", [
    ("v1.4.5", (1, 4, 5)),
    ("1.10.0", (1, 10, 0)),
    ("", (0,)),
    (None, (0,)),
])
def test_normalize_version(v, expected):
    assert ci.normalize_version(v) == expected


@pytest.mark.parametrize("remote,local,newer", [
    ("v1.4.5", "v1.4.4", True),
    ("v1.10.0", "v1.9.9", True),   # numeric, not lexical
    ("v1.4.5", "v1.4.5", False),
    ("v1.4.5", None, True),        # nothing installed
    ("v1.4.4", "v1.4.5", False),
])
def test_is_newer(remote, local, newer):
    assert ci.is_newer(remote, local) is newer
