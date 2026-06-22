"""Tests for the contributor/CI catalog validator."""
from __future__ import annotations

import json

from yonderloft.tools import validate_catalog


def _write(tmp_path, obj):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


def test_clean_manifest_has_no_errors(tmp_path, minimal_manifest_dict):
    # Provide the referenced art so there isn't even a warning.
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "demo.png").write_bytes(b"\x89PNG")
    path = _write(tmp_path, minimal_manifest_dict)
    errors, warnings = validate_catalog.validate(path)
    assert errors == []
    assert warnings == []


def test_missing_art_is_warning_not_error(tmp_path, minimal_manifest_dict):
    path = _write(tmp_path, minimal_manifest_dict)
    errors, warnings = validate_catalog.validate(path)
    assert errors == []
    assert any("art file not found" in w for w in warnings)


def test_duplicate_ids_flagged(tmp_path, minimal_manifest_dict):
    dup = json.loads(json.dumps(minimal_manifest_dict))
    dup["titles"].append(json.loads(json.dumps(minimal_manifest_dict["titles"][0])))
    path = _write(tmp_path, dup)
    errors, _ = validate_catalog.validate(path)
    assert any("duplicate title id" in e for e in errors)


def test_unknown_category_flagged(tmp_path, minimal_manifest_dict):
    bad = json.loads(json.dumps(minimal_manifest_dict))
    bad["titles"][0]["category"] = "does-not-exist"
    path = _write(tmp_path, bad)
    errors, _ = validate_catalog.validate(path)
    assert any("unknown category" in e for e in errors)


def test_client_runtime_requires_client_block(tmp_path, minimal_manifest_dict):
    bad = json.loads(json.dumps(minimal_manifest_dict))
    bad["titles"][0]["runtime"] = "client"  # but no 'client' block
    path = _write(tmp_path, bad)
    errors, _ = validate_catalog.validate(path)
    assert any("requires a 'client' block" in e for e in errors)


def test_multiple_default_servers_flagged(tmp_path, minimal_manifest_dict):
    bad = json.loads(json.dumps(minimal_manifest_dict))
    bad["titles"][0]["servers"].append(
        {"name": "Alt", "url": "https://alt.test/", "default": True}
    )
    path = _write(tmp_path, bad)
    errors, _ = validate_catalog.validate(path)
    assert any("more than one default server" in e for e in errors)


def test_unparseable_manifest_is_error(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{ not json", encoding="utf-8")
    errors, _ = validate_catalog.validate(str(p))
    assert errors and "parse" in errors[0]


def test_main_returns_zero_for_valid(tmp_path, minimal_manifest_dict, capsys):
    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "demo.png").write_bytes(b"\x89PNG")
    path = _write(tmp_path, minimal_manifest_dict)
    assert validate_catalog.main(["prog", path]) == 0


def test_main_returns_one_for_invalid(tmp_path, minimal_manifest_dict):
    bad = json.loads(json.dumps(minimal_manifest_dict))
    bad["titles"][0]["category"] = "ghost"
    path = _write(tmp_path, bad)
    assert validate_catalog.main(["prog", path]) == 1


def test_main_usage_error():
    assert validate_catalog.main(["prog"]) == 2
