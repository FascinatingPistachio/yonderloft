"""Async reachability pinger that drives the online/unstable/offline badges.

A lightweight GET (range-limited) against each server's ``status_url``, with:
  * a short timeout,
  * a per-URL TTL cache so re-displaying a card doesn't re-ping,
  * in-flight de-duplication so the same URL is hit once at a time.

Never blocks the UI: requests go through Soup's async API and results come back
via the ``status-changed`` signal on the main loop.
"""
from __future__ import annotations

import time

from gi.repository import GLib, GObject, Soup

from . import config
from .models import Status

_TTL_SECONDS = 60
_TIMEOUT_SECONDS = 8


class StatusPinger(GObject.Object):
    __gsignals__ = {
        # (status_url, Status)
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
    }

    def __init__(self) -> None:
        super().__init__()
        self._session = Soup.Session(
            user_agent=f"Yonderloft/{config.VERSION}", timeout=_TIMEOUT_SECONDS
        )
        self._cache: dict[str, tuple[float, Status]] = {}
        self._inflight: set[str] = set()

    def cached(self, status_url: str) -> Status:
        entry = self._cache.get(status_url)
        if entry and (time.monotonic() - entry[0]) < _TTL_SECONDS:
            return entry[1]
        return Status.UNKNOWN

    def ping(self, status_url: str, force: bool = False) -> None:
        """Request a status check. Returns immediately; result via signal."""
        if not status_url:
            return
        if not force:
            cached = self.cached(status_url)
            if cached is not Status.UNKNOWN:
                # Re-announce the cached value so late subscribers update.
                GLib.idle_add(self._emit, status_url, cached)
                return
        if status_url in self._inflight:
            return
        message = Soup.Message.new("GET", status_url)
        if message is None:
            self._record(status_url, Status.OFFLINE)
            return
        # Ask for only the first byte; many servers honour it, the rest ignore it.
        message.get_request_headers().append("Range", "bytes=0-0")
        self._inflight.add(status_url)
        self._session.send_async(
            message, GLib.PRIORITY_LOW, None, self._on_response, (status_url, message)
        )

    def _on_response(self, session, result, user_data) -> None:
        status_url, message = user_data
        self._inflight.discard(status_url)
        try:
            session.send_finish(result)
            code = int(message.get_status())
        except GLib.Error:
            self._record(status_url, Status.OFFLINE)
            return
        self._record(status_url, self._classify(code))

    @staticmethod
    def _classify(http_status: int) -> Status:
        if http_status == 0:
            return Status.OFFLINE
        if 200 <= http_status < 400:
            return Status.ONLINE
        if http_status in (408, 429, 502, 503, 504):
            return Status.UNSTABLE
        # 4xx that isn't rate-limiting: reachable but the endpoint is unhappy.
        return Status.UNSTABLE if http_status < 500 else Status.OFFLINE

    def _record(self, status_url: str, status: Status) -> None:
        self._cache[status_url] = (time.monotonic(), status)
        self._emit(status_url, status)

    def _emit(self, status_url: str, status: Status) -> bool:
        self.emit("status-changed", status_url, status)
        return GLib.SOURCE_REMOVE
