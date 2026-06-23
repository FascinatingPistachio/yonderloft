"""Install/update + launch flow for ``client`` titles (e.g. Waddle Forever).

Waddle Forever ships a native Linux AppImage, so no translation layer is needed.
This window fetches the latest GitHub release, downloads the AppImage if it's
missing or out of date, caches it, and launches it. Inside the Flatpak sandbox
AppImages can't use FUSE, so it runs with ``--appimage-extract-and-run``.

Networking and the (large) download run on a worker thread; all UI updates are
marshalled back to the main loop.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import threading
import urllib.request

from gi.repository import Adw, GLib, Gtk

from .. import config
from ..models import Server, Title
from ..client_installer import github_api_latest, is_newer, pick_appimage

_ = __import__("gettext").gettext
_UA = f"Yonderloft/{config.VERSION}"


class ClientInstallWindow(Adw.Window):
    def __init__(self, application, title: Title, server: Server) -> None:
        super().__init__(
            application=application, title=title.name,
            default_width=420, default_height=200, modal=False)
        self._app = application
        self._title = title
        self._server = server
        self._launch_path: str | None = None
        self._dir = os.path.join(config.data_dir(), "clients", title.id)
        os.makedirs(self._dir, exist_ok=True)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=24, margin_bottom=24, margin_start=24, margin_end=24,
                      valign=Gtk.Align.CENTER)
        self._status = Gtk.Label(label=_("Checking for the latest version…"),
                                 wrap=True, xalign=0)
        self._progress = Gtk.ProgressBar(show_text=False)
        self._action = Gtk.Button(visible=False)
        self._action.add_css_class("pill")
        box.append(self._status)
        box.append(self._progress)
        box.append(self._action)
        toolbar.set_content(box)
        self.set_content(toolbar)

    def start(self) -> None:
        self.present()
        threading.Thread(target=self._worker, daemon=True).start()

    # -- Paths --------------------------------------------------------------
    @property
    def _appimage(self) -> str:
        return os.path.join(self._dir, "client.AppImage")

    @property
    def _version_file(self) -> str:
        return os.path.join(self._dir, "VERSION")

    def _installed_version(self) -> str | None:
        try:
            with open(self._version_file, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return None

    # -- Worker (off the main loop) ----------------------------------------
    def _worker(self) -> None:
        try:
            source = self._title.client.get("source_url") or self._title.homepage
            api = github_api_latest(source or "")
            if not api:
                GLib.idle_add(self._fallback, source)
                return
            release = self._get_json(api)
            asset = pick_appimage(release)
            if not asset:
                GLib.idle_add(self._fallback, source)
                return

            if os.path.exists(self._appimage) and not is_newer(
                    asset["version"], self._installed_version()):
                GLib.idle_add(self._set_status, _("Starting %s…") % self._title.name)
                self._launch_path = self._appimage
                GLib.idle_add(self._launch)
                return

            GLib.idle_add(self._set_status,
                          _("Downloading %s…") % asset["version"])
            self._download(asset)
            self._launch_path = self._appimage
            GLib.idle_add(self._launch)
        except Exception as exc:  # network, IO, etc.
            GLib.idle_add(self._error, str(exc))

    def _get_json(self, url: str) -> dict:
        req = urllib.request.Request(
            url, headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def _download(self, asset: dict) -> None:
        req = urllib.request.Request(asset["url"], headers={"User-Agent": _UA})
        tmp = self._appimage + ".part"
        total = asset.get("size", 0)
        done = 0
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    GLib.idle_add(self._set_progress, done / total)
        os.replace(tmp, self._appimage)
        os.chmod(self._appimage, os.stat(self._appimage).st_mode | stat.S_IEXEC |
                 stat.S_IXGRP | stat.S_IXOTH)
        with open(self._version_file, "w", encoding="utf-8") as fh:
            fh.write(asset["version"])

    # -- Main-loop callbacks ------------------------------------------------
    def _set_status(self, text: str) -> bool:
        self._status.set_text(text)
        return GLib.SOURCE_REMOVE

    def _set_progress(self, fraction: float) -> bool:
        self._progress.set_fraction(min(1.0, fraction))
        return GLib.SOURCE_REMOVE

    def _launch(self) -> bool:
        try:
            subprocess.Popen(
                [self._appimage, "--appimage-extract-and-run"],
                cwd=self._dir,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self._error(_("Couldn't start the client: %s") % exc)
            return GLib.SOURCE_REMOVE
        self._set_status(_("%s is running.") % self._title.name)
        self._progress.set_fraction(1.0)
        GLib.timeout_add_seconds(2, self.close)
        return GLib.SOURCE_REMOVE

    def _fallback(self, source: str | None) -> bool:
        # Not a recognised auto-install source — hand off to the browser.
        self._status.set_text(_(
            "This client can't be installed automatically. Opening its "
            "download page instead."))
        self._progress.set_visible(False)
        if source:
            self._action.set_label(_("Open download page"))
            self._action.add_css_class("suggested-action")
            self._action.set_visible(True)
            self._action.connect(
                "clicked", lambda *_a: Gtk.UriLauncher.new(source).launch(self, None, None))
        return GLib.SOURCE_REMOVE

    def _error(self, message: str) -> bool:
        self._status.set_text(_("Couldn't get the client: %s") % message)
        self._progress.set_visible(False)
        return GLib.SOURCE_REMOVE
