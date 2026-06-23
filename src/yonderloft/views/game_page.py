"""A game (or web tool) playing inside the main window, as a page on the content
nav stack.

Pushed onto the main window's AdwNavigationView, so it gets a back button and
feels like one app. Thin chrome: title, an "open in browser" fallback, and a
per-title "clear data" action over the embedded view.

Links that leave the title's own site open in the default browser (with an
Adwaita confirmation, unless turned off in Preferences) rather than navigating
away inside the embedded view.
"""
from __future__ import annotations

from urllib.parse import urlsplit

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gtk, WebKit

from ..models import Server, Title

_ = __import__("gettext").gettext


class GamePage(Adw.NavigationPage):
    def __init__(self, application, title: Title, server: Server, view,
                 page_title: str | None = None, allow_clear: bool = True) -> None:
        super().__init__(title=page_title or title.name)
        self.set_tag(f"game-{title.id}")
        self._app = application
        self._title = title
        self._server = server
        self._view = view
        self._allowed_hosts = self._compute_allowed_hosts(title)

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

    # -- External-link handling --------------------------------------------
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

    def _on_decide_policy(self, _view, decision, decision_type) -> bool:
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        uri = action.get_request().get_uri()
        if not uri or not uri.startswith(("http://", "https://")):
            return False
        host = urlsplit(uri).hostname or ""
        if self._is_allowed(host):
            return False  # same site — navigate normally in-app
        # External: don't navigate inside the game; open in the browser instead.
        decision.ignore()
        if self._app.settings.get_boolean("confirm-external-links"):
            self._confirm_external(uri)
        else:
            self._open_external(uri)
        return True

    def _confirm_external(self, uri: str) -> None:
        dialog = Adw.AlertDialog(
            heading=_("Leave Yonderloft?"),
            body=_("This link opens in your browser:\n\n%s") % uri,
        )
        dialog.add_response("back", _("Go back"))
        dialog.add_response("open", _("Continue"))
        dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("back")
        dialog.connect("response", self._on_confirm_response, uri)
        dialog.present(self.get_root())

    def _on_confirm_response(self, _dialog, response, uri) -> None:
        if response == "open":
            self._open_external(uri)

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
