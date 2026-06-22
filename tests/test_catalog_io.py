"""Tests for the pure catalog I/O: parsing, local fallback ordering, caching."""
from __future__ import annotations

import json

import pytest

from yonderloft import catalog_io
from yonderloft.models import Catalog, UnsupportedSchema


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


def test_parse_bytes_and_str(minimal_manifest_dict):
    raw = json.dumps(minimal_manifest_dict)
    assert isinstance(catalog_io.parse(raw), Catalog)
    assert isinstance(catalog_io.parse(raw.encode()), Catalog)


def test_read_catalog(tmp_path, minimal_manifest_dict):
    path = _write(tmp_path / "m.json", minimal_manifest_dict)
    catalog = catalog_io.read_catalog(path)
    assert catalog.titles[0].id == "demo"


def test_load_first_valid_prefers_earlier_source(tmp_path, minimal_manifest_dict):
    cache = dict(minimal_manifest_dict)
    cache["titles"][0]["name"] = "From Cache"
    bundled = json.loads(json.dumps(minimal_manifest_dict))
    bundled["titles"][0]["name"] = "From Bundle"

    cache_path = _write(tmp_path / "cache.json", cache)
    bundled_path = _write(tmp_path / "bundled.json", bundled)

    catalog, source = catalog_io.load_first_valid(
        [(cache_path, "cache"), (bundled_path, "bundled")]
    )
    assert source == "cache"
    assert catalog.titles[0].name == "From Cache"


def test_load_first_valid_skips_missing_and_corrupt(tmp_path, minimal_manifest_dict):
    missing = str(tmp_path / "nope.json")
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    good = _write(tmp_path / "good.json", minimal_manifest_dict)

    catalog, source = catalog_io.load_first_valid(
        [(missing, "cache"), (str(corrupt), "bundled"), (good, "extra")]
    )
    assert source == "extra"
    assert catalog is not None


def test_load_first_valid_skips_unsupported_schema(tmp_path, minimal_manifest_dict):
    newer = json.loads(json.dumps(minimal_manifest_dict))
    newer["schema_version"] = 999
    older = minimal_manifest_dict

    newer_path = _write(tmp_path / "newer.json", newer)
    older_path = _write(tmp_path / "older.json", older)

    catalog, source = catalog_io.load_first_valid(
        [(newer_path, "cache"), (older_path, "bundled")]
    )
    assert source == "bundled"


def test_load_first_valid_returns_none_when_all_fail(tmp_path):
    catalog, source = catalog_io.load_first_valid([(str(tmp_path / "x"), "cache")])
    assert catalog is None
    assert source == ""


def test_write_cache_is_atomic(tmp_path, minimal_manifest_dict):
    dest = tmp_path / "out.json"
    raw = json.dumps(minimal_manifest_dict).encode()
    catalog_io.write_cache(str(dest), raw)
    assert dest.read_bytes() == raw
    # No leftover temp file.
    assert not (tmp_path / "out.json.tmp").exists()
    # Round-trips back through the parser.
    assert catalog_io.read_catalog(str(dest)).titles[0].id == "demo"
