"""``ruffle`` runtime: render Flash with the bundled Ruffle (Rust/WASM) emulator.

Two modes:

* **Polyfill** (``swf_url`` is null): load the server's own page and inject
  Ruffle's self-hosted ``ruffle.js`` so its ``<embed>``/``<object>`` Flash is
  taken over by Ruffle. This is the common case — the page loads its own SWF.
* **Direct** (``swf_url`` set): build a minimal host page that embeds Ruffle and
  loads the given SWF with the title's flashvars.

Ruffle is bundled with the app (MIT/Apache). Its location is resolved from
``$YONDERLOFT_RUFFLE_DIR`` or ``<pkgdatadir>/ruffle``. If it isn't present the
runtime reports cleanly rather than silently falling back to insecure Flash.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import GLib, WebKit

from .. import config
from ..models import Server, Title
from .base import Runtime, RuntimeNotReady
from .web import make_webview


def ruffle_dir() -> Optional[str]:
    candidates = [os.environ.get("YONDERLOFT_RUFFLE_DIR")]
    candidates.append(os.path.join(config.PKGDATADIR, "ruffle"))
    if not config.INSTALLED:
        candidates.append(os.path.join(config.PKGDATADIR, "build-aux", "ruffle"))
    for path in candidates:
        if path and os.path.exists(os.path.join(path, "ruffle.js")):
            return path
    return None


def _config_script(public_path: str, force_scale: str) -> str:
    cfg = {
        "publicPath": public_path,
        "polyfills": True,
        "autoplay": "on",
        "scale": force_scale or "showAll",
        "contextMenu": "rightClickOnly",
        "warnOnUnsupportedContent": False,
        "logLevel": "error",
    }
    return (
        "window.RufflePlayer = window.RufflePlayer || {};\n"
        f"window.RufflePlayer.config = {json.dumps(cfg)};\n"
    )


class RuffleRuntime(Runtime):
    name = "ruffle"
    embeds = True
    security_note = (
        "Runs through Ruffle, an open-source Flash emulator — no insecure plugin."
    )

    def build_view(self, title: Title, server: Server, network_session):
        rdir = ruffle_dir()
        if rdir is None:
            raise RuntimeNotReady(
                "Ruffle isn't bundled in this build. Reinstall Yonderloft, or set "
                "YONDERLOFT_RUFFLE_DIR to a self-hosted Ruffle.",
                homepage=title.homepage or server.url,
            )

        ruffle_cfg = title.ruffle or {}
        force_scale = ruffle_cfg.get("force_scale", "showAll")
        public_path = GLib.filename_to_uri(rdir + os.sep, None)

        view = make_webview(network_session)

        # Inject config first, then Ruffle itself, at document start so the
        # polyfill catches the page's Flash before it would have run.
        ucm = view.get_user_content_manager()
        ucm.add_script(
            WebKit.UserScript.new(
                _config_script(public_path, force_scale),
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserScriptInjectionTime.START,
                None, None,
            )
        )
        with open(os.path.join(rdir, "ruffle.js"), "r", encoding="utf-8") as fh:
            ruffle_js = fh.read()
        ucm.add_script(
            WebKit.UserScript.new(
                ruffle_js,
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserScriptInjectionTime.START,
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
        flashvars = ruffle_cfg.get("flashvars", {})
        params = json.dumps({"url": swf_url, **flashvars})
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{{margin:0;height:100%;background:#241F31;overflow:hidden}}
#stage{{width:100vw;height:100vh}}</style></head>
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
