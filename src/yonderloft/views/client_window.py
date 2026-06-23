"""Install/update + launch flow for ``client`` titles.

Some revivals ship their own native Linux client instead of running in a browser
(Waddle Forever as an AppImage; Bin Weevils Rewritten as a portable Electron
tarball). These are native Linux apps, so no translation layer is needed. This
window fetches the latest GitHub release, downloads the best runnable asset
(AppImage or tarball) if it's missing or out of date, unpacks it, and launches
it. AppImages run with ``--appimage-extract-and-run`` (FUSE-free, sandbox-safe);
Electron clients are launched with ``--no-sandbox`` since the Flatpak sandbox
already confines them and ``chrome-sandbox`` can't be setuid here.

Networking and the (large) download/extract run on a worker thread; all UI
updates are marshalled back to the main loop.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tarfile
import threading
import urllib.request

from gi.repository import Adw, GLib, Gtk

from .. import config
from ..client_installer import (
    find_launch_target,
    github_api_latest,
    is_newer,
    pick_asset,
)
from ..models import Server, Title

_ = __import__("gettext").gettext
_UA = f"Yonderloft/{config.VERSION}"
_TAR_EXTS = (".tar.xz", ".tar.gz", ".tgz", ".tar.bz2")


class ClientInstallWindow(Adw.Window):
    def __init__(self, application, title: Title, server: Server) -> None:
        super().__init__(
            application=application, title=title.name,
            default_width=440, default_height=200, modal=False)
        self._app = application
        self._title = title
        self._server = server
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

    # -- Install state ------------------------------------------------------
    @property
    def _version_file(self) -> str:
        return os.path.join(self._dir, "VERSION")

    @property
    def _launch_file(self) -> str:
        return os.path.join(self._dir, "LAUNCH")

    def _read_marker(self, path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return None

    def _installed(self) -> tuple[str, str] | None:
        """(kind, launch_path) of the installed client, if usable."""
        marker = self._read_marker(self._launch_file)
        if not marker or "\n" not in marker:
            return None
        kind, path = marker.split("\n", 1)
        return (kind, path) if os.path.exists(path) else None

    # -- Worker (off the main loop) ----------------------------------------
    def _worker(self) -> None:
        try:
            source = self._title.client.get("source_url") or self._title.homepage
            api = github_api_latest(source or "")
            if not api:
                GLib.idle_add(self._fallback, source)
                return
            asset = pick_asset(self._get_json(api))
            if not asset:
                GLib.idle_add(self._fallback, source)
                return

            installed = self._installed()
            if installed and not is_newer(asset["version"],
                                          self._read_marker(self._version_file)):
                GLib.idle_add(self._set_status, _("Starting %s…") % self._title.name)
                GLib.idle_add(self._launch, installed[0], installed[1])
                return

            GLib.idle_add(self._set_status, _("Downloading %s…") % asset["version"])
            archive = self._download(asset)
            GLib.idle_add(self._set_status, _("Unpacking…"))
            kind, target = self._install(asset, archive)

            with open(self._version_file, "w", encoding="utf-8") as fh:
                fh.write(asset["version"])
            with open(self._launch_file, "w", encoding="utf-8") as fh:
                fh.write(f"{kind}\n{target}")
            GLib.idle_add(self._launch, kind, target)
        except Exception as exc:  # network, IO, extraction
            GLib.idle_add(self._error, str(exc))

    def _get_json(self, url: str) -> dict:
        req = urllib.request.Request(
            url, headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def _download(self, asset: dict) -> str:
        ext = next((e for e in _TAR_EXTS if asset["name"].lower().endswith(e)),
                   ".AppImage" if asset["kind"] == "appimage" else ".bin")
        dest = os.path.join(self._dir, f"download{ext}")
        req = urllib.request.Request(asset["url"], headers={"User-Agent": _UA})
        total, done = asset.get("size", 0), 0
        tmp = dest + ".part"
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    GLib.idle_add(self._set_progress, done / total)
        os.replace(tmp, dest)
        return dest

    def _install(self, asset: dict, archive: str) -> tuple[str, str]:
        if asset["kind"] == "appimage":
            self._make_executable(archive)
            return "appimage", archive
        # Tarball: extract fresh, then locate the launch binary.
        app_dir = os.path.join(self._dir, "app")
        shutil.rmtree(app_dir, ignore_errors=True)
        os.makedirs(app_dir, exist_ok=True)
        with tarfile.open(archive, "r:*") as tar:
            try:
                tar.extractall(app_dir, filter="data")  # py>=3.12
            except TypeError:
                tar.extractall(app_dir)
        target = find_launch_target(app_dir, self._title.name)
        if not target:
            raise RuntimeError("couldn't find the client binary in the archive")
        self._make_executable(target)
        return "binary", target

    @staticmethod
    def _make_executable(path: str) -> None:
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP |
                 stat.S_IXOTH)

    # -- Main-loop callbacks ------------------------------------------------
    def _set_status(self, text: str) -> bool:
        self._status.set_text(text)
        return GLib.SOURCE_REMOVE

    def _set_progress(self, fraction: float) -> bool:
        self._progress.set_fraction(min(1.0, fraction))
        return GLib.SOURCE_REMOVE

    def _launch(self, kind: str, target: str) -> bool:
        if kind == "appimage":
            argv = [target, "--appimage-extract-and-run", "--no-sandbox"]
        else:
            argv = [target, "--no-sandbox"]
        try:
            subprocess.Popen(argv, cwd=os.path.dirname(target),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self._error(_("Couldn't start the client: %s") % exc)
            return GLib.SOURCE_REMOVE
        self._set_status(_("%s is running.") % self._title.name)
        self._progress.set_fraction(1.0)
        GLib.timeout_add_seconds(2, self.close)
        return GLib.SOURCE_REMOVE

    def _fallback(self, source: str | None) -> bool:
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
