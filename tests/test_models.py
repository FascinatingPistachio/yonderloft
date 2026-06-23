"""Tests for the typed catalog models and status classification."""
from __future__ import annotations

import pytest

from yonderloft.models import (
    Catalog,
    Runtime,
    Status,
    Title,
    UnsupportedSchema,
    classify_status,
)


def test_parses_minimal_manifest(minimal_manifest_dict):
    catalog = Catalog.from_dict(minimal_manifest_dict)
    assert catalog.schema_version == 1
    assert len(catalog.titles) == 1
    title = catalog.titles[0]
    assert title.id == "demo"
    assert title.runtime is Runtime.WEB
    assert title.default_server.url == "https://example.com/"


def test_rejects_unsupported_schema(minimal_manifest_dict):
    minimal_manifest_dict["schema_version"] = 999
    with pytest.raises(UnsupportedSchema) as exc:
        Catalog.from_dict(minimal_manifest_dict)
    assert exc.value.version == 999


def test_ignores_unknown_fields(minimal_manifest_dict):
    # Forward-compat: extra keys on a same-version manifest are tolerated.
    minimal_manifest_dict["titles"][0]["future_field"] = {"a": 1}
    catalog = Catalog.from_dict(minimal_manifest_dict)
    assert catalog.titles[0].id == "demo"


def test_default_server_falls_back_to_first():
    title = Title.from_dict({
        "id": "x", "name": "X", "category": "c", "runtime": "web", "art": "art/x.png",
        "servers": [
            {"name": "A", "url": "https://a.test/"},
            {"name": "B", "url": "https://b.test/"},
        ],
    })
    # No server marked default -> first one.
    assert title.default_server.name == "A"
    # status_url defaults to url when omitted.
    assert title.default_server.status_url == "https://a.test/"


def test_default_server_honours_flag():
    title = Title.from_dict({
        "id": "x", "name": "X", "category": "c", "runtime": "web", "art": "art/x.png",
        "servers": [
            {"name": "A", "url": "https://a.test/"},
            {"name": "B", "url": "https://b.test/", "default": True},
        ],
    })
    assert title.default_server.name == "B"


@pytest.mark.parametrize("query,expected", [
    ("demo", True),
    ("DEMO", True),       # case-insensitive
    ("html5", True),      # matches a tag
    ("  ", True),         # blank matches everything
    ("missing", False),
])
def test_title_matches(minimal_manifest_dict, query, expected):
    title = Catalog.from_dict(minimal_manifest_dict).titles[0]
    assert title.matches(query) is expected


def test_catalog_lookups(minimal_manifest_dict):
    catalog = Catalog.from_dict(minimal_manifest_dict)
    assert catalog.category("penguins").name == "Penguins"
    assert catalog.category("nope") is None
    assert [t.id for t in catalog.titles_in("penguins")] == ["demo"]
    assert catalog.title("demo").name == "Demo Game"
    assert catalog.title("nope") is None


def test_title_parses_tools_and_player_selector(minimal_manifest_dict):
    minimal_manifest_dict["titles"][0]["player_selector"] = "#game"
    minimal_manifest_dict["titles"][0]["tools"] = [
        {"name": "Register", "url": "https://example.com/register/",
         "hide_selectors": ["nav", ".navbar"]}
    ]
    title = Catalog.from_dict(minimal_manifest_dict).titles[0]
    assert title.player_selector == "#game"
    assert len(title.tools) == 1
    assert title.tools[0].name == "Register"
    assert title.tools[0].hide_selectors == ("nav", ".navbar")


def test_title_art_is_optional():
    title = Title.from_dict({
        "id": "x", "name": "X", "category": "c", "runtime": "web",
        "servers": [{"name": "A", "url": "https://a.test/"}],
    })
    assert title.art == ""
    assert title.tools == ()
    assert title.player_selector == ""


@pytest.mark.parametrize("code,status", [
    (0, Status.OFFLINE),
    (200, Status.ONLINE),
    (204, Status.ONLINE),
    (301, Status.ONLINE),
    (399, Status.ONLINE),
    (403, Status.UNSTABLE),   # reachable but unhappy
    (404, Status.UNSTABLE),
    (429, Status.UNSTABLE),   # rate limited
    (500, Status.OFFLINE),
    (503, Status.UNSTABLE),   # transient
    (504, Status.UNSTABLE),
])
def test_classify_status(code, status):
    assert classify_status(code) is status
