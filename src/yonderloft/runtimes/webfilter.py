"""Ad/tracker blocking for the embedded web views.

WebKitGTK can't run browser extensions like uBlock Origin, but it has a native
content-blocking engine (the same Safari-style JSON rules). We compile a curated
ad/tracker blocklist once at startup into a WebKit content filter and attach it
to every game/tool web view. Everything is guarded so a WebKit API mismatch
degrades to "no blocking" rather than crashing.
"""
from __future__ import annotations

import json

from gi.repository import GLib

from .. import config

# Common ad/tracker/analytics hosts. Curated (not full EasyList), but covers the
# networks most of these sites use.
_BLOCK_HOSTS = [
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "google-analytics.com", "googletagmanager.com", "googletagservices.com",
    "adnxs.com", "amazon-adsystem.com", "scorecardresearch.com",
    "quantserve.com", "quantcount.com", "moatads.com", "taboola.com",
    "outbrain.com", "criteo.com", "criteo.net", "casalemedia.com",
    "rubiconproject.com", "pubmatic.com", "openx.net", "adsrvr.org",
    "2mdn.net", "serving-sys.com", "zedo.com", "adform.net", "yieldmo.com",
    "sharethrough.com", "smartadserver.com", "teads.tv", "bidswitch.net",
    "mathtag.com", "bluekai.com", "agkn.com", "crwdcntrl.net", "demdex.net",
    "everesttech.net", "adroll.com", "hotjar.com", "mouseflow.com",
    "fullstory.com", "mixpanel.com", "amplitude.com", "branch.io",
    "onesignal.com", "connect.facebook.net", "ads-twitter.com",
    "analytics.tiktok.com", "ads.linkedin.com", "adservice.google.com",
    "pagead2.googlesyndication.com", "ad.doubleclick.net",
]

_filter = None
_compiling = False


def _rules_json() -> bytes:
    rules = []
    for host in _BLOCK_HOSTS:
        esc = host.replace(".", "\\.")
        rules.append({
            "trigger": {"url-filter": f"^https?://([^/]*\\.)?{esc}[:/]"},
            "action": {"type": "block"},
        })
    return json.dumps(rules).encode("utf-8")


def compile(on_ready=None) -> None:
    """Compile the blocklist into a content filter (async). Safe to call once."""
    global _compiling
    if _filter is not None or _compiling:
        return
    try:
        import gi
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit

        import os
        store_dir = os.path.join(config.cache_dir(), "contentfilters")
        os.makedirs(store_dir, exist_ok=True)
        store = WebKit.UserContentFilterStore.new(store_dir)
        _compiling = True
        store.save("yonderloft-ads", GLib.Bytes.new(_rules_json()), None,
                   _on_saved, on_ready)
    except Exception:
        _compiling = False


def _on_saved(store, result, on_ready) -> None:
    global _filter, _compiling
    _compiling = False
    try:
        _filter = store.save_finish(result)
    except GLib.Error:
        _filter = None
    if on_ready and _filter is not None:
        on_ready()


def apply_to(user_content_manager) -> None:
    """Attach the ad/tracker filter to a WebView's UserContentManager, if ready."""
    if _filter is not None:
        try:
            user_content_manager.add_filter(_filter)
        except Exception:
            pass
