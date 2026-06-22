"""The title detail page pushed onto the content navigation stack.

Large art, full description, a server picker, a prominent Play button, and a
disclosures panel showing the technical truth (runtime, server URL, sandbox
status) in the mono face.
"""
from __future__ import annotations

from gi.repository import Adw, Gtk

from ..models import Server, Status, Title
from ..runtimes import RuntimeNotReady
from .widgets import StatusDot, runtime_label

_ = __import__("gettext").gettext


class DetailPage(Adw.NavigationPage):
    def __init__(self, application, title: Title, category_name: str) -> None:
        super().__init__(title=title.name)
        self._app = application
        self._title = title
        self._server: Server = title.default_server

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        clamp = Adw.Clamp(maximum_size=720, margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)

        box.append(self._build_hero(category_name))
        if title.description:
            desc = Gtk.Label(label=title.description, wrap=True, xalign=0)
            box.append(desc)
        box.append(self._build_server_picker())
        box.append(self._build_play_button())
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
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        art = Gtk.Box()
        art.add_css_class("cover")
        art.add_css_class("loft-glow")
        art.set_size_request(-1, 220)
        initial = Gtk.Label(label=self._title.name[:1].upper(), vexpand=True)
        initial.add_css_class("title-1")
        art.append(initial)
        hero.append(art)

        name = Gtk.Label(label=self._title.name, xalign=0)
        name.add_css_class("title-1")
        hero.append(name)

        meta = Gtk.Label(
            label=f"{category_name} · {runtime_label(self._title.runtime)}",
            xalign=0,
        )
        meta.add_css_class("dim-label")
        hero.append(meta)

        self._status_dot = StatusDot(self._app.status.cached(self._server.status_url))
        hero.append(self._status_dot)
        return hero

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

    def _build_play_button(self) -> Gtk.Widget:
        self._play = Gtk.Button(label=_("Play"))
        self._play.add_css_class("suggested-action")
        self._play.add_css_class("pill")
        self._play.set_halign(Gtk.Align.CENTER)
        self._play.connect("clicked", self._on_play_clicked)
        return self._play

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
        val.set_ellipsize(3)
        row.add_suffix(val)
        return row, val

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
        # Record recency.
        self._remember_recent()
        try:
            self._app.router.launch(self._title, self._server)
        except RuntimeNotReady as exc:
            self._show_not_ready(exc)

    def _remember_recent(self) -> None:
        settings = self._app.settings
        recent = list(settings.get_strv("recent"))
        if self._title.id in recent:
            recent.remove(self._title.id)
        recent.insert(0, self._title.id)
        settings.set_strv("recent", recent[:24])

    def _show_not_ready(self, exc: RuntimeNotReady) -> None:
        dialog = Adw.AlertDialog(heading=_("Not ready yet"), body=str(exc))
        dialog.add_response("ok", _("OK"))
        if exc.homepage:
            dialog.add_response("open", _("Open homepage"))
            dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self._on_not_ready_response, exc.homepage)
        dialog.present(self)

    def _on_not_ready_response(self, _dialog, response, homepage) -> None:
        if response == "open":
            Gtk.UriLauncher.new(homepage).launch(self.get_root(), None, None)
