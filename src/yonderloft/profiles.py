"""Per-title data isolation.

Each title gets its own directory tree for cookies, local storage, cache and
Flash SOL files. Nothing leaks between servers, and "Clear data" wipes exactly
one title. This matters: revival servers are third parties of varying
trustworthiness.

The WebKit network session is built per title from these paths, so a title's
cookies live only under its own profile.
"""
from __future__ import annotations

import os
import shutil

from . import config


class ProfileManager:
    def __init__(self) -> None:
        self._root = os.path.join(config.data_dir(), "profiles")
        os.makedirs(self._root, exist_ok=True)
        self._sessions: dict = {}  # one WebKit session per title (shared cookies)

    def profile_dir(self, title_id: str) -> str:
        path = os.path.join(self._root, title_id)
        os.makedirs(path, exist_ok=True)
        return path

    def data_path(self, title_id: str) -> str:
        path = os.path.join(self.profile_dir(title_id), "data")
        os.makedirs(path, exist_ok=True)
        return path

    def cache_path(self, title_id: str) -> str:
        path = os.path.join(self.profile_dir(title_id), "cache")
        os.makedirs(path, exist_ok=True)
        return path

    def make_web_session(self, title_id: str):
        """Build an isolated WebKit.NetworkSession for this title.

        Imported lazily so non-GUI tools (the catalog validator) don't pull in
        WebKit.
        """
        if title_id in self._sessions:
            return self._sessions[title_id]

        import gi
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit

        session = WebKit.NetworkSession.new(
            self.data_path(title_id), self.cache_path(title_id)
        )
        # Persist cookies so logins survive between sessions (like a browser).
        # The store lives only under this title's sandboxed profile dir.
        cookies = session.get_cookie_manager()
        cookies.set_persistent_storage(
            os.path.join(self.data_path(title_id), "cookies.sqlite"),
            WebKit.CookiePersistentStorage.SQLITE,
        )
        cookies.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
        self._sessions[title_id] = session
        return session

    def size_bytes(self, title_id: str) -> int:
        total = 0
        for dirpath, _dirs, files in os.walk(self.profile_dir(title_id)):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
        return total

    def clear(self, title_id: str) -> None:
        """Remove all stored data for a single title. Idempotent."""
        self._sessions.pop(title_id, None)
        path = os.path.join(self._root, title_id)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
