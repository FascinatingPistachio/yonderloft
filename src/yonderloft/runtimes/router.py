"""The runtime router — the core launch logic.

Reads ``Title.runtime`` and launches the title the right way: embedded runtimes
open a sandboxed game window hosting a WebView bound to the title's isolated
profile; external runtimes hand off to the title's own client.

Raises :class:`RuntimeNotReady` with a user-facing message when a title can't be
launched (e.g. the ``flash``/``client`` paths still on the roadmap).
"""
from __future__ import annotations

from ..models import Runtime, Server, Title
from .base import Runtime as RuntimeBackend
from .base import RuntimeNotReady
from .client import ClientRuntime
from .flash import FlashRuntime
from .ruffle import RuffleRuntime
from .web import WebRuntime

__all__ = ["RuntimeRouter", "RuntimeNotReady"]


class RuntimeRouter:
    def __init__(self, application) -> None:
        self._app = application
        self._backends: dict[Runtime, RuntimeBackend] = {
            Runtime.WEB: WebRuntime(),
            Runtime.RUFFLE: RuffleRuntime(),
            Runtime.FLASH: FlashRuntime(),
            Runtime.CLIENT: ClientRuntime(),
        }

    def backend_for(self, title: Title) -> RuntimeBackend:
        return self._backends[title.runtime]

    def launch(self, title: Title, server: Server) -> None:
        """Launch a title on a chosen server. May raise RuntimeNotReady."""
        backend = self.backend_for(title)

        if not backend.embeds:
            backend.launch_external(title, server)
            return

        # Embedded: build the WebView against this title's isolated session,
        # then host it in a separate sandboxed game window.
        session = self._app.profiles.make_web_session(title.id)
        view = backend.build_view(title, server, session)

        from ..views.game_window import GameWindow
        window = GameWindow(
            application=self._app,
            title=title,
            server=server,
            view=view,
            security_note=backend.security_note,
        )
        window.present()
