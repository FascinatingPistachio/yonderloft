"""``client`` runtime: manage and launch a title's own native/Electron client.

Yonderloft becomes an installer/wrapper rather than a renderer (e.g. Waddle
Forever, Toontown Rewritten). Full fetch-and-install lands in v0.2. Until then
this opens the client's release/download page so the user can grab it.
"""
from __future__ import annotations

from gi.repository import Gtk

from ..models import Server, Title
from .base import Runtime, RuntimeNotReady


class ClientRuntime(Runtime):
    name = "client"
    embeds = False

    def launch_external(self, title: Title, server: Server) -> None:
        client = title.client or {}
        source = client.get("source_url") or title.homepage or server.url
        # v0.2 will fetch/install/launch the client. For now, hand off to the
        # browser so the user can install it themselves.
        Gtk.UriLauncher.new(source).launch(None, None, None)
        raise RuntimeNotReady(
            client.get("install_hint")
            or "This game ships its own client. Yonderloft will install and "
               "launch it for you in a future version — opening its download "
               "page for now.",
            homepage=source,
        )
