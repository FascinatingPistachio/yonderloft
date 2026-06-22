"""Catalog service: fetch the remote manifest, validate, cache, fall back.

Order of preference when loading:
  1. Freshly fetched remote manifest (cached on success).
  2. Last cached remote manifest.
  3. The manifest bundled with the app (always present).

Emits ``catalog-loaded`` with a :class:`~yonderloft.models.Catalog`, and
``catalog-error`` with a human-readable string when nothing could be loaded.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from gi.repository import GLib, GObject, Soup

from . import config
from .models import Catalog, UnsupportedSchema

_CACHE_NAME = "manifest.json"
_USER_AGENT = f"Yonderloft/{config.VERSION}"


class CatalogService(GObject.Object):
    __gsignals__ = {
        "catalog-loaded": (GObject.SignalFlags.RUN_FIRST, None, (object, str)),
        "catalog-error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        self._session = Soup.Session(user_agent=_USER_AGENT, timeout=10)
        self._catalog: Optional[Catalog] = None

    @property
    def catalog(self) -> Optional[Catalog]:
        return self._catalog

    @property
    def cache_path(self) -> str:
        return os.path.join(config.cache_dir(), _CACHE_NAME)

    # -- Public API ---------------------------------------------------------
    def refresh(self) -> None:
        """Fetch the remote manifest asynchronously, falling back on failure."""
        message = Soup.Message.new("GET", self._url)
        if message is None:  # malformed URL
            self._load_fallback("Catalog URL is invalid.")
            return
        self._session.send_and_read_async(
            message, GLib.PRIORITY_DEFAULT, None, self._on_remote_response, message
        )

    def load_cached_first(self) -> None:
        """Emit a cached/bundled catalog immediately, then refresh in background.

        Lets the grid populate without waiting on the network.
        """
        catalog, source = self._load_local()
        if catalog is not None:
            self._emit_loaded(catalog, source)
        self.refresh()

    # -- Internals ----------------------------------------------------------
    def _on_remote_response(self, session, result, message) -> None:
        try:
            bytes_ = session.send_and_read_finish(result)
            status = message.get_status()
            if status != Soup.Status.OK:
                raise IOError(f"server returned HTTP {int(status)}")
            data = bytes_.get_data()
            catalog = self._parse(data)
        except UnsupportedSchema as exc:
            # A newer manifest we can't read — keep whatever we already showed.
            if self._catalog is None:
                self._load_fallback(
                    f"This catalog needs a newer Yonderloft ({exc}).")
            return
        except Exception as exc:  # network, JSON, validation
            if self._catalog is None:
                self._load_fallback(f"Couldn't fetch the catalog: {exc}")
            return

        # Success — persist to cache and publish.
        try:
            self._write_cache(data)
        except OSError:
            pass
        self._emit_loaded(catalog, "remote")

    def _load_local(self) -> tuple[Optional[Catalog], str]:
        for path, source in ((self.cache_path, "cache"),
                             (config.bundled_catalog_path(), "bundled")):
            try:
                with open(path, "rb") as fh:
                    return self._parse(fh.read()), source
            except (OSError, ValueError, UnsupportedSchema):
                continue
        return None, ""

    def _load_fallback(self, error: str) -> None:
        catalog, source = self._load_local()
        if catalog is not None:
            self._emit_loaded(catalog, source)
        else:
            self.emit("catalog-error", error)

    def _parse(self, raw: bytes) -> Catalog:
        return Catalog.from_dict(json.loads(raw))

    def _write_cache(self, raw: bytes) -> None:
        tmp = self.cache_path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, self.cache_path)

    def _emit_loaded(self, catalog: Catalog, source: str) -> None:
        self._catalog = catalog
        self.emit("catalog-loaded", catalog, source)
