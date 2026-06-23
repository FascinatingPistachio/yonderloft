"""Pure (GTK-free) helpers for resolving cover art.

The fetching service (Soup + GdkPixbuf) lives in ``art_service.py``; this module
holds only logic that can be unit-tested without the GTK stack: where to look
for a title's art, how to scrape an og:image from a landing page, and how to
name the on-disk cache entry.

Resolution order for a title's cover:
  1. The catalog's own ``art/<id>.png`` (resolved against the catalog root URL),
     when the manifest provides one.
  2. The game site's social preview image (``og:image`` / ``twitter:image``),
     fetched at runtime like a browser would.
  3. Nothing — the UI falls back to the lit-window placeholder.
"""
from __future__ import annotations

import hashlib
import os
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlsplit


def catalog_root(catalog_url: str) -> str:
    """The directory URL the manifest lives in, used to resolve relative art."""
    # Drop the trailing filename component (e.g. .../catalog/manifest.json).
    return catalog_url.rsplit("/", 1)[0] + "/" if "/" in catalog_url else catalog_url


def catalog_art_url(catalog_url: str, art: str) -> Optional[str]:
    """Absolute URL of a title's catalog-hosted art, or None if not applicable."""
    if not art:
        return None
    if art.startswith(("http://", "https://")):
        return art
    return urljoin(catalog_root(catalog_url), art)


class _OgImageParser(HTMLParser):
    """Extracts the best preview-image URL from a page's <head>."""

    def __init__(self) -> None:
        super().__init__()
        self.og_image: Optional[str] = None
        self.twitter_image: Optional[str] = None
        self.icon: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            content = a.get("content")
            if not content:
                return
            if key == "og:image" and not self.og_image:
                self.og_image = content
            elif key == "twitter:image" and not self.twitter_image:
                self.twitter_image = content
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "icon" in rel and a.get("href") and not self.icon:
                self.icon = a["href"]

    @property
    def best(self) -> Optional[str]:
        return self.og_image or self.twitter_image or self.icon


def extract_preview_image(html: str, base_url: str) -> Optional[str]:
    """Return an absolute preview-image URL scraped from ``html``, or None.

    Prefers og:image, then twitter:image, then a <link rel="icon">. Relative
    URLs are resolved against ``base_url``.
    """
    parser = _OgImageParser()
    try:
        parser.feed(html)
    except Exception:
        # Malformed markup shouldn't crash art loading.
        return parser.best and urljoin(base_url, parser.best)
    found = parser.best
    return urljoin(base_url, found) if found else None


def cache_base(title_id: str, identity: str) -> str:
    """Cache filename stem for a title, tied to its declared art source.

    When a title's ``art`` changes in the manifest the stem changes, so the old
    cached image is no longer matched and the new art is fetched fresh (instead
    of serving a stale cover forever).
    """
    digest = hashlib.sha1((identity or "og").encode("utf-8")).hexdigest()[:8]
    return f"{title_id}-{digest}"


def cache_name(title_id: str, source_url: str) -> str:
    """Deterministic cache filename: stable per (title, source), keeps extension."""
    ext = os.path.splitext(urlsplit(source_url).path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"):
        ext = ".img"
    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
    return f"{title_id}-{digest}{ext}"


def looks_like_image(content_type: Optional[str], data: bytes) -> bool:
    """Cheap guard so we don't cache an HTML error page as 'art'."""
    if content_type and content_type.split(";")[0].strip().lower().startswith("image/"):
        return True
    # Sniff a few common magic numbers as a fallback.
    return data[:8] in (b"\x89PNG\r\n\x1a\n",) or data[:3] == b"\xff\xd8\xff" \
        or data[:6] in (b"GIF87a", b"GIF89a") or data[:4] == b"RIFF"
