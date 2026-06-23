"""``client`` runtime: install/update and launch a title's own native client.

Yonderloft acts as an installer/manager (e.g. Waddle Forever, which ships a
native Linux AppImage — no translation layer needed). The actual fetch/update/
launch flow, with progress, lives in :class:`ClientInstallWindow`.
"""
from __future__ import annotations

from ..models import Server, Title
from .base import Runtime


class ClientRuntime(Runtime):
    name = "client"
    embeds = False

    def __init__(self, application) -> None:
        self._app = application

    def launch_external(self, title: Title, server: Server) -> None:
        from ..views.client_window import ClientInstallWindow
        window = ClientInstallWindow(self._app, title, server)
        window.start()
