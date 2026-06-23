"""``ruffle`` runtime: render Flash with Ruffle (Rust/WASM), loaded over https.

Why https/CDN and not the bundled copy: Ruffle's self-hosted assets loaded from
a ``file://`` path into an ``https://`` game page are blocked by the browser as
mixed content, so Ruffle never initialises. Loading Ruffle over https from its
CDN avoids that. (The game's own SWF is fetched from the live server as usual.)

"Just the player": for these web titles we also inject a stylesheet that blows
the Ruffle player up to fill the window, so you get the game and not the
surrounding website chrome.
"""
from __future__ import annotations

import json

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import WebKit

from ..models import Server, Title
from .base import Runtime
from .web import make_webview

# Official Ruffle self-hosted bundle over https (resolves its own wasm chunks).
RUFFLE_SRC = "https://unpkg.com/@ruffle-rs/ruffle"

# Fill the window with just the game. We style the Ruffle host elements (and raw
# Flash embeds) — not the inner <canvas>, which lives in shadow DOM. No DOM is
# removed, so the game's own scripts keep working; the player just covers the
# page chrome.
_ISOLATE_CSS = """
html, body { margin: 0 !important; overflow: hidden !important; background: #241F31 !important; }
ruffle-player, ruffle-object, ruffle-embed,
embed[src$=".swf"], object[data$=".swf"],
embed[type*="flash"], object[type*="flash"] {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important;
  max-height: none !important;
  margin: 0 !important;
  border: 0 !important;
  z-index: 2147483647 !important;
}
"""


def _ruffle_config(force_scale: str) -> dict:
    return {
        "polyfills": True,
        "autoplay": "on",
        "scale": force_scale or "showAll",
        "letterbox": "on",
        "contextMenu": "rightClickOnly",
        "warnOnUnsupportedContent": False,
        "logLevel": "error",
        "unmuteOverlay": "hidden",
    }


def _loader_script(config: dict) -> str:
    # Set Ruffle config, then load Ruffle from the CDN. Injected at document
    # start so the polyfill catches the page's Flash.
    return (
        "window.RufflePlayer = window.RufflePlayer || {};\n"
        f"window.RufflePlayer.config = {json.dumps(config)};\n"
        "(function () {\n"
        "  var s = document.createElement('script');\n"
        f"  s.src = {json.dumps(RUFFLE_SRC)};\n"
        "  s.async = false;\n"
        "  (document.head || document.documentElement).appendChild(s);\n"
        "})();\n"
    )


class RuffleRuntime(Runtime):
    name = "ruffle"
    embeds = True
    security_note = (
        "Played through Ruffle (open-source, sandboxed) — no insecure plugin."
    )

    def build_view(self, title: Title, server: Server, network_session):
        ruffle_cfg = title.ruffle or {}
        view = make_webview(network_session)

        ucm = view.get_user_content_manager()
        from . import webfilter
        webfilter.apply_to(ucm)
        ucm.add_script(
            WebKit.UserScript.new(
                _loader_script(_ruffle_config(ruffle_cfg.get("force_scale", "showAll"))),
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserScriptInjectionTime.START,
                None, None,
            )
        )
        ucm.add_style_sheet(
            WebKit.UserStyleSheet.new(
                _ISOLATE_CSS,
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserStyleLevel.USER,
                None, None,
            )
        )

        swf_url = ruffle_cfg.get("swf_url")
        if swf_url:
            view.load_html(self._direct_host_page(swf_url, ruffle_cfg), server.url)
        else:
            view.load_uri(server.url)
        return view

    @staticmethod
    def _direct_host_page(swf_url: str, ruffle_cfg: dict) -> str:
        params = json.dumps({"url": swf_url, **ruffle_cfg.get("flashvars", {})})
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{{margin:0;height:100%;background:#241F31;overflow:hidden}}
#stage{{position:fixed;inset:0}}</style>
<script src="{RUFFLE_SRC}"></script></head>
<body><div id="stage"></div>
<script>
window.addEventListener('load', function () {{
  var ruffle = window.RufflePlayer.newest();
  var player = ruffle.createPlayer();
  document.getElementById('stage').appendChild(player);
  player.style.width = '100%'; player.style.height = '100%';
  player.load({params});
}});
</script></body></html>"""
