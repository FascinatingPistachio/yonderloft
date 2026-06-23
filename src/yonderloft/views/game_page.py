"""A game (or web tool) playing inside the main window, as a page on the content
nav stack.

Link handling:
* Navigating to one of the title's declared tools (e.g. its register page)
  opens that tool inside Yonderloft (navbar hidden) instead of in the game view.
* Links that leave the title's own site open in the default browser, behind an
  Adwaita confirmation (unless turned off in Preferences). Only one confirmation
  shows at a time; if several pile up, a red "Close all" clears them.
"""
from __future__ import annotations

from urllib.parse import urlsplit

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import Adw, GLib, Gtk, WebKit

from ..models import Server, Title

_ = __import__("gettext").gettext
_MAX_QUEUE = 20


class GamePage(Adw.NavigationPage):
    def __init__(self, application, title: Title, server: Server, view,
                 page_title: str | None = None, allow_clear: bool = True,
                 is_tool: bool = False) -> None:
        super().__init__(title=page_title or title.name)
        self.set_tag(f"game-{title.id}" + ("-tool" if is_tool else ""))
        self._app = application
        self._title = title
        self._server = server
        self._view = view
        self._is_tool = is_tool
        self._allowed_hosts = self._compute_allowed_hosts(title)
        self._ext_queue: list[str] = []
        self._ext_dialog_open = False

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title=page_title or title.name, subtitle=server.name))

        if allow_clear:
            clear = Gtk.Button(icon_name="user-trash-symbolic")
            clear.set_tooltip_text(_("Clear this game's saved data"))
            clear.connect("clicked", self._on_clear_data)
            header.pack_end(clear)

        browser = Gtk.Button(icon_name="web-browser-symbolic")
        browser.set_tooltip_text(_("Open in your browser"))
        browser.connect("clicked", self._on_open_browser)
        header.pack_end(browser)

        toolbar.add_top_bar(header)
        view.set_hexpand(True)
        view.set_vexpand(True)
        toolbar.set_content(view)
        self.set_child(toolbar)

        view.connect("decide-policy", self._on_decide_policy)

    # -- Navigation policy --------------------------------------------------
    @staticmethod
    def _compute_allowed_hosts(title: Title) -> set[str]:
        hosts: set[str] = set()
        for server in title.servers:
            host = urlsplit(server.url).hostname
            if host:
                hosts.add(host)
        for extra in (title.homepage,) + tuple(t.url for t in title.tools):
            host = urlsplit(extra).hostname
            if host:
                hosts.add(host)
        return hosts

    def _is_allowed(self, host: str) -> bool:
        return any(host == a or host.endswith("." + a) for a in self._allowed_hosts)

    def _matching_tool(self, uri: str):
        for tool in self._title.tools:
            if uri.rstrip("/").startswith(tool.url.rstrip("/")):
                return tool
        return None

    def _on_decide_policy(self, _view, decision, decision_type) -> bool:
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        if not uri or not uri.startswith(("http://", "https://")):
            return False

        # A link to one of this title's tools opens the tool (clean) in-app,
        # not in the game view. (Not while already inside that tool page.)
        if not self._is_tool:
            tool = self._matching_tool(uri)
            if tool is not None:
                decision.ignore()
                self._app.router.launch_tool(self._title, tool)
                return True

        host = urlsplit(uri).hostname or ""
        if self._is_allowed(host):
            return False  # same site — navigate normally in-app
        decision.ignore()
        self._enqueue_external(uri)
        return True

    # -- External-link confirmations (one at a time) -----------------------
    def _enqueue_external(self, uri: str) -> None:
        if not self._app.settings.get_boolean("confirm-external-links"):
            self._open_external(uri)
            return
        if uri in self._ext_queue or len(self._ext_queue) >= _MAX_QUEUE:
            return
        self._ext_queue.append(uri)
        if not self._ext_dialog_open:
            self._show_next_external()

    def _show_next_external(self) -> bool:
        if not self._ext_queue:
            return GLib.SOURCE_REMOVE
        uri = self._ext_queue[0]
        self._ext_dialog_open = True
        dialog = Adw.AlertDialog(
            heading=_("Leave Yonderloft?"),
            body=_("This link opens in your browser:\n\n%s") % uri,
        )
        dialog.add_response("back", _("Go back"))
        dialog.add_response("open", _("Continue"))
        dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        if len(self._ext_queue) > 1:
            dialog.add_response("closeall",
                                _("Close all (%d)") % len(self._ext_queue))
            dialog.set_response_appearance("closeall",
                                           Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("back")
        dialog.connect("response", self._on_ext_response)
        dialog.present(self.get_root())
        return GLib.SOURCE_REMOVE

    def _on_ext_response(self, _dialog, response) -> None:
        self._ext_dialog_open = False
        uri = self._ext_queue.pop(0) if self._ext_queue else None
        if response == "open" and uri:
            self._open_external(uri)
        elif response == "closeall":
            self._ext_queue.clear()
        if self._ext_queue:
            GLib.idle_add(self._show_next_external)

    def _open_external(self, uri: str) -> None:
        Gtk.UriLauncher.new(uri).launch(self.get_root(), None, None)

    # -- Header actions -----------------------------------------------------
    def _on_open_browser(self, _button) -> None:
        Gtk.UriLauncher.new(self._server.url).launch(self.get_root(), None, None)

    def _on_clear_data(self, _button) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Clear saved data?"),
            body=_(
                "This removes %s's cookies, logins and saved progress on this "
                "computer. The game itself isn't affected."
            ) % self._title.name,
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("clear", _("Clear data"))
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_clear_response)
        dialog.present(self.get_root())

    def _on_clear_response(self, _dialog, response) -> None:
        if response == "clear":
            self._app.profiles.clear(self._title.id)
            nav = self.get_ancestor(Adw.NavigationView)
            if nav is not None:
                nav.pop()
