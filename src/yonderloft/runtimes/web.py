"""``web`` runtime: a plain WebKitGTK view for HTML5 rewrites."""
from __future__ import annotations

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import WebKit

from ..models import Server, Title
from .base import Runtime


def make_webview(network_session) -> "WebKit.WebView":
    """A WebView bound to an isolated, per-title network session."""
    view = WebKit.WebView(network_session=network_session)
    settings = view.get_settings()
    settings.set_property("enable-developer-extras", False)
    settings.set_property("enable-write-console-messages-to-stdout", False)
    settings.set_property(
        "user-agent",
        # Some revivals gate on a desktop browser UA; present a generic one.
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Yonderloft",
    )
    return view


class WebRuntime(Runtime):
    name = "web"
    embeds = True

    def build_view(self, title: Title, server: Server, network_session):
        view = make_webview(network_session)
        view.load_uri(server.url)
        return view
