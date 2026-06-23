"""Main window: navigation split view with a sidebar and the card grid."""
from __future__ import annotations

from gi.repository import Adw, Gio, Gtk

from .models import Catalog, Title
from .views.detail import DetailPage
from .views.grid import GameGrid

_ = __import__("gettext").gettext

# Pinned sidebar rows that aren't catalog categories.
_PIN_ALL = "__all__"
_PIN_FAVORITES = "__favorites__"
_PIN_RECENT = "__recent__"


class YonderloftWindow(Adw.ApplicationWindow):
    def __init__(self, application) -> None:
        super().__init__(application=application, title="Yonderloft")
        self._app = application
        self._catalog: Catalog | None = None

        self.set_size_request(360, 480)
        self._bind_window_state()

        self._grid = GameGrid(application.status, application.art)
        self._grid.connect("title-activated", self._on_title_activated)

        self._content_nav = Adw.NavigationView()
        self._content_nav.add(self._build_grid_page())

        self._split = Adw.NavigationSplitView(
            sidebar=self._build_sidebar(),
            content=Adw.NavigationPage(title="Yonderloft", child=self._content_nav),
        )
        self._split.set_min_sidebar_width(200)
        self._split.set_max_sidebar_width(280)

        self.set_content(self._split)

        application.catalog.connect("catalog-loaded", self._on_catalog_loaded)
        application.catalog.connect("catalog-error", self._on_catalog_error)

    # -- Window state -------------------------------------------------------
    def _bind_window_state(self) -> None:
        settings = self._app.settings
        self.set_default_size(
            settings.get_int("window-width"), settings.get_int("window-height")
        )
        if settings.get_boolean("window-maximized"):
            self.maximize()
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, *_args) -> bool:
        settings = self._app.settings
        if not self.is_maximized():
            width, height = self.get_default_size()
            settings.set_int("window-width", width)
            settings.set_int("window-height", height)
        settings.set_boolean("window-maximized", self.is_maximized())
        return False

    # -- Sidebar ------------------------------------------------------------
    def _build_sidebar(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        self._search_button = Gtk.ToggleButton(icon_name="system-search-symbolic")
        self._search_button.connect("toggled", self._on_search_toggled)
        header.pack_end(self._search_button)
        header.pack_end(self._build_menu_button())
        toolbar.add_top_bar(header)

        self._search_bar, self._search_entry = self._build_search()
        toolbar.add_top_bar(self._search_bar)

        self._sidebar_list = Gtk.ListBox()
        self._sidebar_list.add_css_class("navigation-sidebar")
        self._sidebar_list.connect("row-selected", self._on_sidebar_row_selected)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(self._sidebar_list)
        toolbar.set_content(scroller)

        self._populate_pins()
        return Adw.NavigationPage(title="Yonderloft", child=toolbar)

    def _populate_pins(self) -> None:
        for key, label, icon in (
            (_PIN_ALL, _("All"), "view-grid-symbolic"),
            (_PIN_FAVORITES, _("Favorites"), "starred-symbolic"),
            (_PIN_RECENT, _("Recent"), "document-open-recent-symbolic"),
        ):
            self._sidebar_list.append(self._sidebar_row(key, label, icon))
        self._sidebar_list.select_row(self._sidebar_list.get_row_at_index(0))

    def _sidebar_row(self, key: str, label: str, icon: str | None = None) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.filter_key = key  # type: ignore[attr-defined]
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        if icon:
            box.append(Gtk.Image.new_from_icon_name(icon))
        box.append(Gtk.Label(label=label, xalign=0))
        row.set_child(box)
        return row

    def _rebuild_categories(self, catalog: Catalog) -> None:
        # Drop any previously-added category rows (index >= 3), keep the 3 pins.
        while True:
            row = self._sidebar_list.get_row_at_index(3)
            if row is None:
                break
            self._sidebar_list.remove(row)
        # Only show categories that actually have titles.
        for category in catalog.categories:
            if catalog.titles_in(category.id):
                self._sidebar_list.append(self._sidebar_row(category.id, category.name))

    # -- Search -------------------------------------------------------------
    def _build_search(self) -> tuple[Gtk.SearchBar, Gtk.SearchEntry]:
        entry = Gtk.SearchEntry(hexpand=True)
        entry.set_placeholder_text(_("Search games"))
        entry.connect("search-changed", self._on_search_changed)
        bar = Gtk.SearchBar()
        bar.set_child(entry)
        bar.connect_entry(entry)
        bar.set_key_capture_widget(self)
        return bar, entry

    def _build_menu_button(self) -> Gtk.MenuButton:
        menu = Gio.Menu()
        menu.append(_("Refresh catalog"), "app.refresh")
        menu.append(_("About Yonderloft"), "app.about")
        menu.append(_("Quit"), "app.quit")
        button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        return button

    # -- Content ------------------------------------------------------------
    def _build_grid_page(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._content_title = Adw.WindowTitle(title=_("All games"), subtitle="")
        header.set_title_widget(self._content_title)
        toolbar.add_top_bar(header)
        toolbar.set_content(self._grid)
        page = Adw.NavigationPage(title=_("All games"), child=toolbar)
        page.set_tag("grid")
        return page

    # -- Catalog wiring -----------------------------------------------------
    def _on_catalog_loaded(self, _service, catalog: Catalog, source: str) -> None:
        self._catalog = catalog
        self._rebuild_categories(catalog)
        self._grid.set_catalog(catalog)
        self._update_content_subtitle(source)

    def _on_catalog_error(self, _service, message: str) -> None:
        # No catalog at all — show the message in the content title area.
        self._content_title.set_subtitle(message)

    def _update_content_subtitle(self, source: str) -> None:
        if self._catalog is None:
            return
        n = len(self._catalog.titles)
        note = {"remote": "", "cache": _(" · offline (cached)"),
                "bundled": _(" · offline (bundled)")}.get(source, "")
        self._content_title.set_subtitle(_("%d games") % n + note)

    # -- Events -------------------------------------------------------------
    def _on_sidebar_row_selected(self, _list, row) -> None:
        if row is None:
            return
        key = getattr(row, "filter_key", _PIN_ALL)
        # Selecting anything in the sidebar pops back to the grid.
        self._content_nav.pop_to_tag("grid")
        self._apply_filter(key)

    def _apply_filter(self, key: str) -> None:
        if key == _PIN_ALL:
            self._grid.set_titles_filter(None)
            self._content_title.set_title(_("All games"))
        elif key == _PIN_FAVORITES:
            self._grid.set_titles_filter(set(self._app.settings.get_strv("favorites")))
            self._content_title.set_title(_("Favorites"))
        elif key == _PIN_RECENT:
            self._grid.set_titles_filter(
                set(self._app.settings.get_strv("recent")), keep_order=True
            )
            self._content_title.set_title(_("Recent"))
        else:
            self._grid.set_category(key)
            cat = self._catalog.category(key) if self._catalog else None
            self._content_title.set_title(cat.name if cat else key)

    def _on_search_toggled(self, button: Gtk.ToggleButton) -> None:
        self._search_bar.set_search_mode(button.get_active())

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._grid.set_query(entry.get_text())

    def _on_title_activated(self, _grid, title: Title) -> None:
        category = self._catalog.category(title.category) if self._catalog else None
        page = DetailPage(self._app, title, category.name if category else title.category)
        self._content_nav.push(page)
