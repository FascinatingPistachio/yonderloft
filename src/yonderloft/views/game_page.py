"""A game playing inside the main window, as a page on the content nav stack.

Pushed onto the main window's AdwNavigationView, so it gets a back button and
feels like one app (rather than a separate window). Thin chrome: title, an
"open in browser" fallback, and a per-title "clear data" action, over the
embedded runtime view.
"""
from __future__ import annotations

from gi.repository import Adw, Gtk

from ..models import Server, Title

_ = __import__("gettext").gettext


class GamePage(Adw.NavigationPage):
    def __init__(self, application, title: Title, server: Server, view,
                 security_note: str = "") -> None:
        super().__init__(title=title.name)
        self.set_tag(f"game-{title.id}")
        self._app = application
        self._title = title
        self._server = server

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()  # back button is added by the NavigationView
        header.set_title_widget(Adw.WindowTitle(title=title.name, subtitle=server.name))

        clear = Gtk.Button(icon_name="user-trash-symbolic")
        clear.set_tooltip_text(_("Clear this game's saved data"))
        clear.connect("clicked", self._on_clear_data)
        header.pack_end(clear)

        browser = Gtk.Button(icon_name="web-browser-symbolic")
        browser.set_tooltip_text(_("Open this game in your browser"))
        browser.connect("clicked", self._on_open_browser)
        header.pack_end(browser)

        toolbar.add_top_bar(header)
        if security_note:
            toolbar.add_top_bar(Adw.Banner(title=security_note, revealed=True))

        view.set_hexpand(True)
        view.set_vexpand(True)
        toolbar.set_content(view)
        self.set_child(toolbar)

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
            # Leave the game so the next launch starts from a clean profile.
            nav = self.get_ancestor(Adw.NavigationView)
            if nav is not None:
                nav.pop()
