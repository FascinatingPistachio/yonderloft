"""The card grid — a FlowBox of game cards with live status badges.

Note: the README sketches an ``AdwFlowBox``; GTK/Adwaita ships ``Gtk.FlowBox``,
which is what we use (libadwaita has no flow box of its own).
"""
from __future__ import annotations

from gi.repository import GObject, Gtk, Pango

from ..models import Catalog, Status, Title
from .widgets import StatusDot, runtime_label

_ = __import__("gettext").gettext


class GameCard(Gtk.Button):
    """A single game card. A flat button so the whole card is one click target."""

    def __init__(self, title: Title, category_name: str) -> None:
        super().__init__()
        self.title = title
        self.add_css_class("game-card")
        self.add_css_class("flat")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(190, -1)

        # Cover — placeholder lit-window glow until art loads.
        cover = Gtk.Box()
        cover.add_css_class("cover")
        cover.add_css_class("loft-glow")
        cover.set_size_request(190, 150)
        initial = Gtk.Label(label=title.name[:1].upper())
        initial.add_css_class("title-1")
        initial.set_vexpand(True)
        cover.append(initial)
        box.append(cover)

        name = Gtk.Label(label=title.name, xalign=0, wrap=True, lines=2)
        name.add_css_class("title")
        name.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(name)

        meta = Gtk.Label(
            label=f"{category_name} · {runtime_label(title.runtime)}", xalign=0
        )
        meta.add_css_class("runtime-badge")
        box.append(meta)

        self.status_dot = StatusDot()
        box.append(self.status_dot)

        self.set_child(box)


class GameGrid(Gtk.ScrolledWindow):
    __gsignals__ = {
        "title-activated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, status_pinger) -> None:
        super().__init__(hexpand=True, vexpand=True)
        self._status = status_pinger
        # status_url -> list[GameCard] to update when a ping returns.
        self._by_status_url: dict[str, list[GameCard]] = {}
        self._catalog: Catalog | None = None
        self._category_filter: str | None = None
        self._id_filter: set[str] | None = None  # for Favorites / Recent
        self._id_order: list[str] | None = None   # preserve Recent ordering
        self._query: str = ""

        self._status.connect("status-changed", self._on_status_changed)

        self._flow = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=8,
            min_children_per_line=2,
            row_spacing=18,
            column_spacing=18,
            homogeneous=True,
            selection_mode=Gtk.SelectionMode.NONE,
        )
        self._flow.set_margin_top(18)
        self._flow.set_margin_bottom(18)
        self._flow.set_margin_start(18)
        self._flow.set_margin_end(18)

        self._empty = self._build_empty_state()

        self._stack = Gtk.Stack()
        self._stack.add_named(self._flow, "grid")
        self._stack.add_named(self._empty, "empty")
        self.set_child(self._stack)

    # -- Public API ---------------------------------------------------------
    def set_catalog(self, catalog: Catalog) -> None:
        self._catalog = catalog
        self._rebuild()

    def set_category(self, category_id: str | None) -> None:
        self._category_filter = category_id
        self._id_filter = None
        self._id_order = None
        self._rebuild()

    def set_titles_filter(self, ids: set[str] | None, keep_order: bool = False) -> None:
        """Restrict to a set of title IDs (Favorites / Recent). None = All."""
        self._category_filter = None
        self._id_filter = ids
        self._id_order = list(ids) if (ids is not None and keep_order) else None
        self._rebuild()

    def set_query(self, query: str) -> None:
        self._query = query or ""
        self._rebuild()

    # -- Building -----------------------------------------------------------
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
            card = GameCard(title, category.name if category else title.category)
            card.connect("clicked", self._on_card_clicked)
            self._flow.append(card)

            status_url = title.default_server.status_url
            self._by_status_url.setdefault(status_url, []).append(card)
            card.status_dot.set_status(self._status.cached(status_url))

        # Kick off status checks for everything now visible.
        for status_url in self._by_status_url:
            self._status.ping(status_url)

    def _build_empty_state(self) -> Gtk.Widget:
        status = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER,
                         vexpand=True)
        status.add_css_class("loft-glow")
        icon = Gtk.Image.new_from_icon_name("uk.aaronworld.Yonderloft-symbolic")
        icon.set_pixel_size(96)
        icon.add_css_class("dim-label")
        heading = Gtk.Label(label=_("Nothing here"))
        heading.add_css_class("title-2")
        body = Gtk.Label(label=_("No games match. Try another category or search."))
        body.add_css_class("dim-label")
        status.append(icon)
        status.append(heading)
        status.append(body)
        return status

    # -- Status wiring ------------------------------------------------------
    def _on_status_changed(self, _pinger, status_url: str, status: Status) -> None:
        for card in self._by_status_url.get(status_url, []):
            card.status_dot.set_status(status)

    def _on_card_clicked(self, card: GameCard) -> None:
        self.emit("title-activated", card.title)
