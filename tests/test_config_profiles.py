"""Tests for XDG path resolution and per-title profile isolation."""
from __future__ import annotations

import importlib

from yonderloft import config
from yonderloft.profiles import ProfileManager


def test_cache_and_data_dirs_follow_xdg(isolated_xdg):
    assert config.cache_dir().startswith(str(isolated_xdg["cache"]))
    assert config.data_dir().startswith(str(isolated_xdg["data"]))
    # Directories are created on demand.
    assert config.cache_dir().endswith("yonderloft")


def test_profiles_are_isolated_per_title(isolated_xdg):
    pm = ProfileManager()
    a = pm.profile_dir("game-a")
    b = pm.profile_dir("game-b")
    assert a != b
    assert "game-a" in a and "game-b" in b
    # Data and cache subdirs exist and differ.
    assert pm.data_path("game-a") != pm.cache_path("game-a")


def test_clear_removes_only_one_title(isolated_xdg):
    pm = ProfileManager()
    a_data = pm.data_path("game-a")
    b_data = pm.data_path("game-b")
    (importlib.import_module("pathlib").Path(a_data) / "cookies.txt").write_text("a")
    (importlib.import_module("pathlib").Path(b_data) / "cookies.txt").write_text("b")

    assert pm.size_bytes("game-a") > 0
    pm.clear("game-a")
    assert pm.size_bytes("game-a") == 0       # gone
    assert pm.size_bytes("game-b") > 0        # untouched


def test_clear_is_idempotent(isolated_xdg):
    pm = ProfileManager()
    pm.clear("never-created")  # must not raise
