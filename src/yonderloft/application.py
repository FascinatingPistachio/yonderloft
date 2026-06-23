"""AdwApplication: wires services together and owns the main window."""
from __future__ import annotations

import os

from gi.repository import Adw, Gdk, Gio, Gtk

from . import config
from .art_service import ArtService
from .catalog import CatalogService
from .profiles import ProfileManager
from .runtimes import RuntimeRouter
from .status import StatusPinger
from .window import YonderloftWindow

_ = __import__("gettext").gettext


class YonderloftApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=config.APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.settings = Gio.Settings.new(config.APP_ID)
        self.profiles = ProfileManager()
        self.status = StatusPinger()
        self.catalog = CatalogService(self.settings.get_string("catalog-url"))
        self.art = ArtService(self.settings.get_string("catalog-url"))
        self.router = RuntimeRouter(self)

        self._window: YonderloftWindow | None = None
        self._setup_actions()

    @property
    def window(self) -> "YonderloftWindow | None":
        return self._window

    # -- Lifecycle ----------------------------------------------------------
    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._load_css()
        from .runtimes import webfilter
        webfilter.compile()

    def do_activate(self) -> None:
        if self._window is None:
            self._window = YonderloftWindow(application=self)
        self._window.present()
        # Populate from cache/bundled instantly, then refresh from network.
        self.catalog.load_cached_first()

    # -- Setup --------------------------------------------------------------
    def _setup_actions(self) -> None:
        self._add_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self._add_action("about", self._on_about)
        self._add_action("preferences", self._on_preferences, ["<primary>comma"])
        self._add_action("refresh", lambda *_: self.catalog.refresh(), ["<primary>r"])

    def _add_action(self, name, callback, accels=None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if accels:
            self.set_accels_for_action(f"app.{name}", accels)

    def _load_css(self) -> None:
        css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # -- Actions ------------------------------------------------------------
    def _on_preferences(self, *_args) -> None:
        dialog = Adw.PreferencesDialog()
        page = Adw.PreferencesPage(
            title=_("General"), icon_name="preferences-system-symbolic")
        group = Adw.PreferencesGroup(title=_("Browsing"))
        row = Adw.SwitchRow(
            title=_("Confirm external links"),
            subtitle=_("Ask before opening links that leave a game's site in "
                       "your browser."))
        self.settings.bind("confirm-external-links", row, "active",
                           Gio.SettingsBindFlags.DEFAULT)
        group.add(row)
        page.add(group)
        dialog.add(page)
        dialog.present(self._window)

    def _on_about(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name="Yonderloft",
            application_icon=config.APP_ID,
            developer_name="Aaron",
            version=config.VERSION,
            comments=_("The attic where the old web lives on."),
            website="https://aaronworld.uk/yonderloft",
            issue_url="https://gitlab.com/FascinatingPistachio/yonderloft/-/issues",
            license_type=Gtk.License.GPL_3_0,
            copyright="© 2026 Aaron",
        )
        about.set_disclaimer(_(
            "Independent project. Not affiliated with or endorsed by any rights "
            "holder or revival project. No game content is hosted or distributed "
            "by Yonderloft."
        ))
        about.present(self._window)
