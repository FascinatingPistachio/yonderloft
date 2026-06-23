"""Common runtime interface.

A runtime is one of two shapes:

* **Embedded** (`embeds = True`): produces a GTK widget (a WebView) that the
  game window hosts. Used by ``web``, ``ruffle`` and ``flash``.
* **External** (`embeds = False`): launches the title's own client as a separate
  process. Used by ``client``.

Runtimes never reach into UI chrome; they return a widget or perform a launch.
"""
from __future__ import annotations

from ..models import Server, Title


class Runtime:
    #: machine name, matches Title.runtime
    name: str = ""
    #: True if launch() returns a Gtk.Widget to embed in a game window.
    embeds: bool = True
    #: One-line honest security disclosure shown in the detail view, or "".
    security_note: str = ""
    #: Whether this runtime is a legacy/unmaintained stack (drives a warning).
    legacy: bool = False

    def build_view(self, title: Title, server: Server, network_session):
        """Return a Gtk.Widget rendering the title. Embedded runtimes only."""
        raise NotImplementedError

    def launch_external(self, title: Title, server: Server) -> None:
        """Launch the title's own client. External runtimes only."""
        raise NotImplementedError
