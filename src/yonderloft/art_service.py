"""Async cover-art fetcher with an on-disk cache.

For each title it resolves a cover in this order (see :mod:`yonderloft.art`):
catalog-hosted art → the site's og:image → nothing. Fetched bytes are cached
under the app data dir keyed by title id, so a title is only fetched once.

Results come back as a Gdk.Paintable via the per-request callback, on the main
loop. Never blocks the UI.
"""
from __future__ import annotations

import glob
import os
from typing import Callable, Optional

from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Soup

from . import art, config
from .models import Title

_ART_PX = 320  # cover art is decoded/scaled to roughly card resolution


class ArtService(GObject.Object):
    def __init__(self, catalog_url: str) -> None:
        super().__init__()
        self._catalog_url = catalog_url
        self._session = Soup.Session(
            user_agent=f"Yonderloft/{config.VERSION}", timeout=15)
        self._dir = os.path.join(config.data_dir(), "art")
        os.makedirs(self._dir, exist_ok=True)

    def set_catalog_url(self, url: str) -> None:
        self._catalog_url = url

    # -- Public API ---------------------------------------------------------
    def load(self, title: Title, callback: Callable[[Optional[Gdk.Paintable]], None]) -> None:
        """Resolve and load a title's cover, calling ``callback`` with a
        Gdk.Paintable or None (caller shows a placeholder)."""
        cached = self._cached_path(title.id)
        if cached:
            callback(self._to_paintable(cached))
            return

        source = art.catalog_art_url(self._catalog_url, title.art)
        if source:
            self._fetch_image(source, title, callback, allow_scrape=True)
        else:
            self._scrape_then_fetch(title, callback)

    # -- Cache --------------------------------------------------------------
    def _cached_path(self, title_id: str) -> Optional[str]:
        matches = glob.glob(os.path.join(self._dir, f"{title_id}.*"))
        return matches[0] if matches else None

    def _save(self, title_id: str, source_url: str, data: bytes) -> str:
        ext = os.path.splitext(art.cache_name(title_id, source_url))[1]
        path = os.path.join(self._dir, f"{title_id}{ext}")
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
        return path

    # -- Fetching -----------------------------------------------------------
    def _fetch_image(self, url, title, callback, allow_scrape) -> None:
        message = Soup.Message.new("GET", url)
        if message is None:
            self._next(title, callback, allow_scrape)
            return
        self._session.send_and_read_async(
            message, GLib.PRIORITY_LOW, None,
            self._on_image, (title, callback, allow_scrape, url, message))

    def _on_image(self, session, result, data) -> None:
        title, callback, allow_scrape, url, message = data
        try:
            body = session.send_and_read_finish(result).get_data()
            ok = int(message.get_status()) == 200
            ctype = message.get_response_headers().get_one("content-type")
        except GLib.Error:
            body, ok, ctype = b"", False, None

        if ok and body and art.looks_like_image(ctype, body):
            path = self._save(title.id, url, body)
            callback(self._to_paintable(path))
            return
        self._next(title, callback, allow_scrape)

    def _next(self, title, callback, allow_scrape) -> None:
        if allow_scrape:
            self._scrape_then_fetch(title, callback)
        else:
            callback(None)

    def _scrape_then_fetch(self, title, callback) -> None:
        page = title.homepage or (title.default_server.url if title.servers else "")
        if not page:
            callback(None)
            return
        message = Soup.Message.new("GET", page)
        if message is None:
            callback(None)
            return
        self._session.send_and_read_async(
            message, GLib.PRIORITY_LOW, None,
            self._on_page, (title, callback, page, message))

    def _on_page(self, session, result, data) -> None:
        title, callback, page, message = data
        try:
            html = session.send_and_read_finish(result).get_data().decode(
                "utf-8", "replace")
        except GLib.Error:
            callback(None)
            return
        image_url = art.extract_preview_image(html, page)
        if image_url:
            self._fetch_image(image_url, title, callback, allow_scrape=False)
        else:
            callback(None)

    # -- Decoding -----------------------------------------------------------
    def _to_paintable(self, path: str) -> Optional[Gdk.Paintable]:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, _ART_PX, _ART_PX, True)
            return Gdk.Texture.new_for_pixbuf(pixbuf)
        except GLib.Error:
            return None
