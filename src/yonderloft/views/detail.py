"""The title detail page pushed onto the content navigation stack.

Large art, full description, a server picker, a prominent Play button, and a
disclosures panel showing the technical truth (runtime, server URL, sandbox
status) in the mono face.
"""
from __future__ import annotations

from gi.repository import Adw, Gio, Gtk, Pango

from ..models import Server, Status, Title
from .widgets import StatusDot, runtime_label

_ = __import__("gettext").gettext


class DetailPage(Adw.NavigationPage):
    def __init__(self, application, title: Title, category_name: str) -> None:
        super().__init__(title=title.name)
        self._app = application
        self._title = title
        self._server: Server = title.default_server

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._fav_button = Gtk.ToggleButton()
        self._fav_button.set_tooltip_text(_("Add to Favorites"))
        self._fav_button.set_active(title.id in application.settings.get_strv("favorites"))
        self._update_fav_icon()
        self._fav_button.connect("toggled", self._on_fav_toggled)
        header.pack_end(self._fav_button)
        toolbar.add_top_bar(header)

        clamp = Adw.Clamp(maximum_size=820, margin_top=20, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)

        box.append(self._build_hero(category_name))
        if title.description:
            desc = Gtk.Label(label=title.description, wrap=True, xalign=0)
            box.append(desc)
        box.append(self._build_server_picker())
        if title.tools:
            box.append(self._build_tools())
        box.append(self._build_disclosures())

        clamp.set_child(box)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(clamp)
        toolbar.set_content(scroller)
        self.set_child(toolbar)

        # Live status for the selected server.
        self._app.status.connect("status-changed", self._on_status_changed)
        self._app.status.ping(self._server.status_url)

    # -- Sections -----------------------------------------------------------
    def _build_hero(self, category_name: str) -> Gtk.Widget:
        # Immersive banner: the art fills the hero; a scrim darkens the lower
        # half so the title, status and a prominent amber Play sit over it.
        overlay = Gtk.Overlay()
        overlay.add_css_class("hero")
        overlay.set_size_request(-1, 300)

        self._art_box = Gtk.Box()
        self._art_box.add_css_class("hero")
        self._art_box.add_css_class("cover-ph")
        self._art_box.set_size_request(-1, 300)
        ph_icon = Gtk.Image.new_from_icon_name("uk.aaronworld.Yonderloft-symbolic")
        ph_icon.set_pixel_size(72)
        ph_icon.add_css_class("cover-ph-icon")
        ph_icon.set_hexpand(True)
        ph_icon.set_vexpand(True)
        self._art_box.append(ph_icon)
        overlay.set_child(self._art_box)

        scrim = Gtk.Box()
        scrim.add_css_class("hero-scrim")
        overlay.add_overlay(scrim)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      valign=Gtk.Align.END, margin_start=22, margin_end=22,
                      margin_top=18, margin_bottom=20)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5,
                       hexpand=True, valign=Gtk.Align.END)
        name = Gtk.Label(label=self._title.name, xalign=0, wrap=True)
        name.add_css_class("hero-title")
        name.add_css_class("title-1")
        info.append(name)
        sub = Gtk.Label(
            label=f"{category_name} · {runtime_label(self._title.runtime)}",
            xalign=0)
        sub.add_css_class("hero-sub")
        info.append(sub)
        self._status_dot = StatusDot(self._app.status.cached(self._server.status_url))
        info.append(self._status_dot)
        bar.append(info)

        self._play = Gtk.Button(label=_("Play"), valign=Gtk.Align.END)
        self._play.add_css_class("loft-play")
        self._play.connect("clicked", self._on_play_clicked)
        bar.append(self._play)
        overlay.add_overlay(bar)

        self._app.art.load(self._title, self._on_art_loaded)
        return overlay

    def _on_art_loaded(self, paintable) -> None:
        if paintable is None:
            return
        child = self._art_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._art_box.remove(child)
            child = nxt
        picture = Gtk.Picture(paintable=paintable)
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_size_request(-1, 300)
        picture.add_css_class("hero")
        self._art_box.remove_css_class("cover-ph")
        self._art_box.append(picture)

    def _build_server_picker(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title=_("Server"))
        if len(self._title.servers) == 1:
            row = Adw.ActionRow(title=self._server.name, subtitle=self._server.url)
            row.add_css_class("property")
            group.add(row)
            return group

        model = Gtk.StringList()
        for server in self._title.servers:
            model.append(server.name)
        combo = Adw.ComboRow(title=_("Server"), model=model)
        default_index = self._title.servers.index(self._server)
        combo.set_selected(default_index)
        combo.connect("notify::selected", self._on_server_selected)
        group.add(combo)
        return group

    def _build_tools(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title=_("Tools"))
        for tool in self._title.tools:
            row = Adw.ActionRow(title=tool.name, activatable=True)
            row.add_prefix(Gtk.Image.new_from_icon_name(tool.icon))
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", self._on_tool_activated, tool)
            group.add(row)
        return group

    def _on_tool_activated(self, _row, tool) -> None:
        self._app.router.launch_tool(self._title, tool)

    def _build_disclosures(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title=_("Under the hood"))
        backend = self._app.router.backend_for(self._title)

        runtime_row, _ignored = self._mono_row(_("Runtime"), runtime_label(self._title.runtime))
        server_row, self._server_url_label = self._mono_row(_("Server URL"), self._server.url)
        sandbox_row, _ignored = self._mono_row(_("Profile"), _("isolated · per-game"))
        group.add(runtime_row)
        group.add(server_row)
        group.add(sandbox_row)

        if backend.security_note:
            note = Adw.ActionRow(title=backend.security_note)
            note.set_subtitle_lines(0)
            icon = Gtk.Image.new_from_icon_name(
                "dialog-warning-symbolic" if backend.legacy else "security-high-symbolic"
            )
            note.add_prefix(icon)
            group.add(note)

        if self._title.notes:
            group.add(Adw.ActionRow(title=self._title.notes))
        return group

    def _mono_row(self, label: str, value: str) -> tuple[Adw.ActionRow, Gtk.Label]:
        row = Adw.ActionRow(title=label)
        val = Gtk.Label(label=value, xalign=1, selectable=True)
        val.add_css_class("mono")
        val.set_ellipsize(Pango.EllipsizeMode.END)
        row.add_suffix(val)
        return row, val

    # -- Favorites ----------------------------------------------------------
    def _update_fav_icon(self) -> None:
        active = self._fav_button.get_active()
        self._fav_button.set_icon_name("starred-symbolic" if active
                                       else "non-starred-symbolic")

    def _on_fav_toggled(self, _button) -> None:
        settings = self._app.settings
        favorites = list(settings.get_strv("favorites"))
        if self._fav_button.get_active():
            if self._title.id not in favorites:
                favorites.append(self._title.id)
        else:
            favorites = [f for f in favorites if f != self._title.id]
        settings.set_strv("favorites", favorites)
        self._update_fav_icon()

    # -- Events -------------------------------------------------------------
    def _on_server_selected(self, combo, _param) -> None:
        self._server = self._title.servers[combo.get_selected()]
        self._server_url_label.set_text(self._server.url)
        self._status_dot.set_status(self._app.status.cached(self._server.status_url))
        self._app.status.ping(self._server.status_url)

    def _on_status_changed(self, _pinger, status_url: str, status: Status) -> None:
        if status_url == self._server.status_url:
            self._status_dot.set_status(status)

    def _on_play_clicked(self, _button) -> None:
        # Everything but offline-capable titles (e.g. Waddle) needs a connection.
        needs_internet = "offline" not in self._title.tags
        if needs_internet and not Gio.NetworkMonitor.get_default().get_network_available():
            self._show_offline()
            return
        self._remember_recent()
        self._app.router.launch(self._title, self._server)

    def _show_offline(self) -> None:
        dialog = Adw.AlertDialog(
            heading=_("No internet connection"),
            body=_("%s needs an internet connection to play, and you appear to "
                   "be offline. Reconnect and try again.") % self._title.name,
        )
        dialog.add_response("ok", _("OK"))
        dialog.present(self.get_root())

    def _remember_recent(self) -> None:
        settings = self._app.settings
        recent = list(settings.get_strv("recent"))
        if self._title.id in recent:
            recent.remove(self._title.id)
        recent.insert(0, self._title.id)
        settings.set_strv("recent", recent[:24])
