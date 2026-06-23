"""Card workspace display dashboard matrix module view."""
from __future__ import annotations

from gi.repository import GObject, Gtk, Pango, Adw

from ..models import Catalog, Status, Title
from .widgets import StatusDot, runtime_label

_ = __import__("gettext").gettext

_COVER_W = 240
_COVER_H = 135  # Perfect 16:9 widescreen asset factor ratio


class GameCard(Gtk.Button):
    def __init__(self, title: Title, category_name: str, art_service=None) -> None:
        super().__init__()
        self.title = title
        self.add_css_class("game-card")
        self.add_css_class("flat")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(_COVER_W, -1)

        # Isolated structural frame container wrapper
        self.frame = Gtk.Box()
        self.frame.add_css_class("cover-frame")
        self.frame.set_size_request(_COVER_W, _COVER_H)

        overlay = Gtk.Overlay()
        overlay.set_size_request(_COVER_W, _COVER_H)

        self._cover = Gtk.Box()
        self._cover.add_css_class("cover")
        self._cover.add_css_class("cover-ph")
        self._cover.set_size_request(_COVER_W, _COVER_H)
        
        ph_icon = Gtk.Image.new_from_icon_name("uk.aaronworld.Yonderloft-symbolic")
        ph_icon.set_pixel_size(48)
        ph_icon.add_css_class("cover-ph-icon")
        ph_icon.set_hexpand(True)
        ph_icon.set_vexpand(True)
        self._cover.append(ph_icon)
        overlay.set_child(self._cover)

        scrim = Gtk.Box(valign=Gtk.Align.END)
        scrim.add_css_class("cover-scrim")
        scrim.set_size_request(-1, 52)
        overlay.add_overlay(scrim)

        runtime_chip = Gtk.Label(
            label=runtime_label(title.runtime),
            halign=Gtk.Align.START, 
            valign=Gtk.Align.END
        )
        runtime_chip.add_css_class("cover-chip")
        overlay.add_overlay(runtime_chip)

        self.status_dot = StatusDot()
        self.status_dot.add_css_class("status-dot")
        self.status_dot.set_halign(Gtk.Align.END)
        self.status_dot.set_valign(Gtk.Align.START)
        overlay.add_overlay(self.status_dot)

        self.frame.append(overlay)
        box.append(self.frame)

        if art_service is not None:
            art_service.load(title, self._on_art_loaded)

        name = Gtk.Label(label=title.name, xalign=0, wrap=True, lines=2)
        name.add_css_class("title")
        name.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(name)

        category = Gtk.Label(label=category_name, xalign=0)
        category.add_css_class("runtime-badge")
        box.append(category)

        self.set_child(box)

    def _on_art_loaded(self, paintable) -> None:
        if paintable is None:
            return
        child = self._cover.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._cover.remove(child)
            child = nxt
            
        picture = Gtk.Picture(paintable=paintable)
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_size_request(_COVER_W, _COVER_H)
        
        self._cover.remove_css_class("cover-ph")
        self._cover.append(picture)


class GameGrid(Gtk.ScrolledWindow):
    __gsignals__ = {
        "title-activated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, status_pinger, art_service=None) -> None:
        super().__init__(hexpand=True, vexpand=True)
        self._status = status_pinger
        self._art = art_service
        self._by_status_url: dict[str, list[GameCard]] = {}
        self._catalog: Catalog | None = None
        self._category_filter: str | None = None
        self._id_filter: set[str] | None = None
        self._id_order: list[str] | None = None
        self._query: str = ""

        self._status.connect("status-changed", self._on_status_changed)

        self._flow = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=8,
            min_children_per_line=2,
            row_spacing=24,
            column_spacing=20,
            homogeneous=True,
            selection_mode=Gtk.SelectionMode.NONE,
        )
        self._flow.set_margin_top(24)
        self._flow.set_margin_bottom(24)
        self._flow.set_margin_start(24)
        self._flow.set_margin_end(24)

        self._empty = self._build_empty_state()

        self._stack = Gtk.Stack()
        self._stack.add_named(self._flow, "grid")
        self._stack.add_named(self._empty, "empty")
        
        # Smooth state shifting transitions 
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(200)
        
        self.set_child(self._stack)

    def set_catalog(self, catalog: Catalog) -> None:
        self._catalog = catalog
        self._rebuild()

    def set_category(self, category_id: str | None) -> None:
        self._category_filter = category_id
        self._id_filter = None
        self._id_order = None
        self._rebuild()

    def set_titles_filter(self, ids: set[str] | None, keep_order: bool = False) -> None:
        self._category_filter = None
        self._id_filter = ids
        self._id_order = list(ids) if (ids is not None and keep_order) else None
        self._rebuild()

    def set_query(self, query: str) -> None:
        self._query = query or ""
        self._rebuild()

    def _visible_titles(self) -> list[Title]:
        if self._catalog is None:
            return []
        titles = list(self._catalog.titles)
        if self._category_filter:
            titles = [t for t in titles if t.category == self._category_filter]
        if self._id_filter is not None:
            titles = [t for t in titles if t.id in self._id_filter]
            if self._id_order is not None:
                rank = {tid: i for i, tid in enumerate(self._id_order)}
                titles.sort(key=lambda t: rank.get(t.id, len(rank)))
        if self._query:
            titles = [t for t in titles if t.matches(self._query)]
        return titles

    def _rebuild(self) -> None:
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt
        self._by_status_url.clear()

        titles = self._visible_titles()
        if not titles:
            self._stack.set_visible_child_name("empty")
            return
        self._stack.set_visible_child_name("grid")

        for title in titles:
            category = self._catalog.category(title.category)
            card = GameCard(
                title, 
                category.name if category else title.category,
                art_service=self._art
            )
            card.connect("clicked", self._on_card_clicked)
            self._flow.append(card)

            status_url = title.default_server.status_url
            self._by_status_url.setdefault(status_url, []).append(card)
            card.status_dot.set_status(self._status.cached(status_url))

        for status_url in self._by_status_url:
            self._status.ping(status_url)

    def _build_empty_state(self) -> Gtk.Widget:
        # Rebuilt empty layout matching Adw.StatusPage standard spacing rulesets
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.add_css_class("loft-status-page")
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_vexpand(True)

        icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        icon.set_pixel_size(72)
        icon.add_css_class("dim-label")
        box.append(icon)

        title = Gtk.Label(label=_("No Matching Games Found"))
        title.add_css_class("title")
        box.append(title)

        desc = Gtk.Label(label=_("Try checking your spelling or select a different filter category."))
        desc.add_css_class("dim-label")
        box.append(desc)

        return box

    def _on_status_changed(self, _pinger, status_url: str, status: Status) -> None:
        for card in self._by_status_url.get(status_url, []):
            card.status_dot.set_status(status)

    def _on_card_clicked(self, card: GameCard) -> None:
        self.emit("title-activated", card.title)