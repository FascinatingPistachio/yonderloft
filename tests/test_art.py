"""Tests for the GTK-free cover-art resolution helpers."""
from __future__ import annotations

import pytest

from yonderloft import art

CATALOG = "https://gitlab.com/u/yonderloft/-/raw/main/catalog/manifest.json"


def test_catalog_root_strips_filename():
    assert art.catalog_root(CATALOG).endswith("/catalog/")


def test_catalog_art_url_relative():
    url = art.catalog_art_url(CATALOG, "art/demo.png")
    assert url == "https://gitlab.com/u/yonderloft/-/raw/main/catalog/art/demo.png"


def test_catalog_art_url_absolute_passthrough():
    assert art.catalog_art_url(CATALOG, "https://x.test/a.png") == "https://x.test/a.png"


def test_catalog_art_url_none_when_empty():
    assert art.catalog_art_url(CATALOG, "") is None


@pytest.mark.parametrize("html,expected", [
    ('<meta property="og:image" content="https://x.test/c.png">', "https://x.test/c.png"),
    ('<meta name="twitter:image" content="/t.png">', "https://site.test/t.png"),
    ('<link rel="shortcut icon" href="favicon.ico">', "https://site.test/favicon.ico"),
    ('<title>nothing here</title>', None),
])
def test_extract_preview_image(html, expected):
    assert art.extract_preview_image(html, "https://site.test/page") == expected


def test_extract_prefers_og_over_twitter_and_icon():
    html = (
        '<link rel="icon" href="/i.png">'
        '<meta name="twitter:image" content="/t.png">'
        '<meta property="og:image" content="/og.png">'
    )
    assert art.extract_preview_image(html, "https://s.test/") == "https://s.test/og.png"


def test_cache_name_is_deterministic_and_keeps_ext():
    a = art.cache_name("demo", "https://x.test/cover.png?v=2")
    b = art.cache_name("demo", "https://x.test/cover.png?v=2")
    assert a == b
    assert a.startswith("demo-") and a.endswith(".png")


def test_cache_name_unknown_ext_falls_back():
    assert art.cache_name("demo", "https://x.test/image").endswith(".img")


def test_looks_like_image_by_content_type():
    assert art.looks_like_image("image/png", b"")


def test_looks_like_image_by_magic():
    assert art.looks_like_image(None, b"\x89PNG\r\n\x1a\n....")
    assert art.looks_like_image(None, b"\xff\xd8\xff\xe0....")


def test_looks_like_image_rejects_html():
    assert not art.looks_like_image("text/html", b"<!DOCTYPE html><html>")
