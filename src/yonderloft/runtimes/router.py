"""The runtime router — the core launch logic.

Reads ``Title.runtime`` and launches the title the right way: embedded runtimes
push a game page hosting a WebView bound to the title's isolated profile;
external runtimes hand off to the title's own client.
"""
from __future__ import annotations

from ..models import Runtime, Server, Title
from .base import Runtime as RuntimeBackend
from .client import ClientRuntime
from .flash import FlashRuntime
from .ruffle import RuffleRuntime
from .web import WebRuntime

__all__ = ["RuntimeRouter"]


class RuntimeRouter:
    def __init__(self, application) -> None:
        self._app = application
        self._backends: dict[Runtime, RuntimeBackend] = {
            Runtime.WEB: WebRuntime(),
            Runtime.RUFFLE: RuffleRuntime(),
            Runtime.FLASH: FlashRuntime(),
            Runtime.CLIENT: ClientRuntime(application),
        }

    def backend_for(self, title: Title) -> RuntimeBackend:
        return self._backends[title.runtime]

    def launch(self, title: Title, server: Server) -> None:
        """Launch a title on a chosen server."""
        backend = self.backend_for(title)

        if not backend.embeds:
            backend.launch_external(title, server)
            return

        # Embedded: build the WebView against this title's isolated session,
        # then host it as a page inside the main window.
        session = self._app.profiles.make_web_session(title.id)
        view = backend.build_view(title, server, session)

        from ..views.game_page import GamePage
        page = GamePage(self._app, title, server, view)
        self._app.window.play_game(page)

    def launch_tool(self, title: Title, tool) -> None:
        """Open a title's web tool (e.g. its register page) inside the window."""
        from ..models import Server
        from ..views.game_page import GamePage
        from .web import build_page

        session = self._app.profiles.make_web_session(title.id)
        view = build_page(session, tool.url, hide_selectors=tool.hide_selectors)
        pseudo = Server(name=tool.name, url=tool.url, status_url=tool.url)
        page = GamePage(self._app, title, pseudo, view,
                        page_title=tool.name, allow_clear=False, is_tool=True)
        self._app.window.play_game(page)
