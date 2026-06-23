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


# -- asset_kind / pick_asset ------------------------------------------------

@pytest.mark.parametrize("name,kind", [
    ("App-x86_64.AppImage", "appimage"),
    ("BWR_Installer_1.0.4-x64-Manual-Linux.tar.xz", "tarball"),
    ("client-linux.tar.gz", "tarball"),
    ("BWR_Installer_1.0.4-amd64.deb", None),       # .deb not auto-run
    ("Setup-Windows.tar.gz", None),                # windows tarball skipped
    ("App-mac.tar.gz", None),                       # mac tarball skipped
    ("readme.txt", None),
])
def test_asset_kind(name, kind):
    assert ci.asset_kind(name) == kind


def test_pick_asset_prefers_appimage_over_tarball():
    release = {"tag_name": "v2", "assets": [
        {"name": "App-linux.tar.gz", "browser_download_url": "https://x/t", "size": 1},
        {"name": "App-x86_64.AppImage", "browser_download_url": "https://x/a", "size": 2},
    ]}
    picked = ci.pick_asset(release)
    assert picked["kind"] == "appimage" and picked["url"].endswith("/a")


def test_pick_asset_takes_linux_tarball_when_no_appimage():
    # Mirrors the real Bin Weevils Rewritten 1.0.4 asset list.
    release = {"tag_name": "1.0.4", "assets": [
        {"name": "BWR_Installer_1.0.4-amd64.deb", "browser_download_url": "https://x/d", "size": 1},
        {"name": "BWR_Installer_1.0.4-ia32.exe", "browser_download_url": "https://x/e", "size": 1},
        {"name": "BWR_Installer_1.0.4-x64-Manual-Linux.tar.xz", "browser_download_url": "https://x/t", "size": 2},
    ]}
    picked = ci.pick_asset(release)
    assert picked["kind"] == "tarball"
    assert picked["url"].endswith("/t")
    assert picked["version"] == "1.0.4"


def test_pick_asset_none_when_no_linux_asset():
    release = {"tag_name": "v1", "assets": [
        {"name": "win.exe", "browser_download_url": "u"},
        {"name": "mac.dmg", "browser_download_url": "u"},
    ]}
    assert ci.pick_asset(release) is None


# -- find_launch_target -----------------------------------------------------

def _make_executable(path):
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x7fELF")
    os.chmod(path, 0o755)


def test_find_launch_target_picks_electron_binary(tmp_path):
    # Mirror the BWR tarball layout.
    root = tmp_path / "BWR Installer 1.0.4-x64"
    _make_executable(root / "bwrewritten")
    _make_executable(root / "chrome-sandbox")            # helper, excluded
    _make_executable(root / "chrome_crashpad_handler")   # helper, excluded
    _make_executable(root / "libffmpeg.so")              # library, excluded by ext
    (root / "resources" / "app").mkdir(parents=True)
    (root / "resources.pak").write_bytes(b"x")
    target = ci.find_launch_target(str(root), "Bin Weevils Rewritten")
    assert target is not None and target.endswith("/bwrewritten")


def test_find_launch_target_prefers_hint_match(tmp_path):
    root = tmp_path / "app"
    _make_executable(root / "launcher")
    _make_executable(root / "binweevils")  # matches hint token
    target = ci.find_launch_target(str(root), "Bin Weevils")
    assert target.endswith("/binweevils")


def test_find_launch_target_none_when_no_executable(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "data.pak").write_bytes(b"x")
    assert ci.find_launch_target(str(root), "x") is None
