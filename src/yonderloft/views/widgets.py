"""Small shared widgets and helpers used across views."""
from __future__ import annotations

from gi.repository import Gtk

from ..models import Status

_STATUS_LABEL = {
    Status.ONLINE: "online",
    Status.UNSTABLE: "unstable",
    Status.OFFLINE: "offline",
    Status.UNKNOWN: "checking…",
}


class StatusDot(Gtk.Box):
    """A coloured dot plus a text label, driven by a :class:`Status`."""

    def __init__(self, status: Status = Status.UNKNOWN) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._dot = Gtk.Box()
        self._dot.add_css_class("status-dot")
        self._label = Gtk.Label(xalign=0)
        self._label.add_css_class("caption")
        self.append(self._dot)
        self.append(self._label)
        self.set_status(status)

    def set_status(self, status: Status) -> None:
        for name in ("online", "unstable", "offline", "unknown"):
            self._dot.remove_css_class(name)
        self._dot.add_css_class(status.value)
        self._label.set_text(_STATUS_LABEL.get(status, "checking…"))


def runtime_label(runtime) -> str:
    """Human label for a runtime, for the card/detail metadata line."""
    return {
        "ruffle": "Ruffle",
        "flash": "Flash (sandboxed)",
        "web": "Web",
        "client": "Native client",
    }.get(getattr(runtime, "value", runtime), str(runtime))
