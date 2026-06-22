"""The sandboxed game window — a separate window, not the launcher chrome.

Minimal by design: the game surface, a thin header with the title, a back/close,
and a "Clear data" affordance that wipes only this title's profile.
"""
from __future__ import annotations

from gi.repository import Adw, Gtk

from ..models import Server, Title

_ = __import__("gettext").gettext


class GameWindow(Adw.Window):
    def __init__(self, application, title: Title, server: Server, view, security_note: str = "") -> None:
        super().__init__(
            application=application,
            title=title.name,
            default_width=1024,
            default_height=720,
        )
        self._app = application
        self._title = title
        self.set_icon_name(application.get_application_id())

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_title(True)

        title_widget = Adw.WindowTitle(title=title.name, subtitle=server.name)
        header.set_title_widget(title_widget)

        # Clear-data button (wipes only this title).
        clear = Gtk.Button(icon_name="user-trash-symbolic")
        clear.set_tooltip_text(_("Clear this game's saved data"))
        clear.connect("clicked", self._on_clear_data)
        header.pack_end(clear)

        toolbar.add_top_bar(header)

        view.set_hexpand(True)
        view.set_vexpand(True)
        toolbar.set_content(view)

        if security_note:
            banner = Adw.Banner(title=security_note, revealed=True)
            toolbar.add_top_bar(banner)

        self.set_content(toolbar)

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
        dialog.present(self)

    def _on_clear_response(self, _dialog, response) -> None:
        if response == "clear":
            self._app.profiles.clear(self._title.id)
            # Close so the next launch starts from a clean, freshly-created profile.
            self.close()
