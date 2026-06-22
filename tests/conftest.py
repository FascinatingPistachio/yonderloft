"""Shared test fixtures. Puts ``src`` on the path so ``import yonderloft`` works
without an install, and exposes repo paths.

These tests deliberately exercise only the GTK-free layer (models, catalog I/O,
status classification, config, profiles, the validator) — everything that does
not require a display. The GUI shell is verified by building the Flatpak.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def real_manifest() -> Path:
    return REPO_ROOT / "catalog" / "manifest.json"


@pytest.fixture
def real_schema() -> Path:
    return REPO_ROOT / "catalog" / "schema.json"


@pytest.fixture
def isolated_xdg(tmp_path, monkeypatch):
    """Point XDG cache/data dirs at a tmp location for the duration of a test."""
    cache = tmp_path / "cache"
    data = tmp_path / "data"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    return {"cache": cache, "data": data}


@pytest.fixture
def minimal_manifest_dict() -> dict:
    return {
        "schema_version": 1,
        "updated": "2026-06-22",
        "categories": [{"id": "penguins", "name": "Penguins"}],
        "titles": [
            {
                "id": "demo",
                "name": "Demo Game",
                "category": "penguins",
                "runtime": "web",
                "art": "art/demo.png",
                "servers": [
                    {"name": "Main", "url": "https://example.com/",
                     "status_url": "https://example.com/", "default": True}
                ],
                "tags": ["html5"],
            }
        ],
    }
