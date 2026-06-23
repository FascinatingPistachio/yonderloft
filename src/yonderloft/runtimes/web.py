"""``web`` runtime: a plain WebKitGTK view for HTML5 / self-hosted-Ruffle titles.

Also provides the shared page builder used by the ``ruffle`` runtime and by
per-title tools (e.g. a register page with its navbar hidden):

* **isolate a player** — hoist one in-page element (by CSS selector) to fill the
  window and hide everything else, so you get just the game, not the website.
* **hide selectors** — drop chrome like a site navbar.
"""
from __future__ import annotations

import json

import gi

gi.require_version("WebKit", "6.0")
from gi.repository import WebKit

from ..models import Server, Title
from .base import Runtime

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Yonderloft"
)


def make_webview(network_session) -> "WebKit.WebView":
    """A WebView bound to an isolated, per-title network session."""
    view = WebKit.WebView(network_session=network_session)
    settings = view.get_settings()
    settings.set_property("enable-developer-extras", False)
    settings.set_property("enable-write-console-messages-to-stdout", False)
    settings.set_property("user-agent", _USER_AGENT)
    return view


def _isolation_script(selector: str) -> "WebKit.UserScript":
    # Hoist the game element to fullscreen, hide its siblings up the tree, then
    # nudge a resize so games that size to their container rescale.
    source = """
(function () {
  var SEL = %s;
  var target = null;
  function hideOthers() {
    var node = target;
    while (node && node.parentElement) {
      var p = node.parentElement, kids = p.children;
      for (var i = 0; i < kids.length; i++) {
        if (kids[i] !== node) kids[i].style.setProperty('display', 'none', 'important');
      }
      if (p === document.body) break;
      node = p;
    }
  }
  function apply() {
    target = document.querySelector(SEL);
    if (!target) return false;
    var fs = 'position:fixed;inset:0;left:0;top:0;width:100vw;height:100vh;'
           + 'max-width:none;max-height:none;margin:0;padding:0;z-index:2147483647;';
    target.setAttribute('style', (target.getAttribute('style') || '') + ';' + fs);
    var a = target.parentElement;
    while (a && a !== document.body) {
      a.style.setProperty('overflow', 'visible', 'important');
      a.style.setProperty('transform', 'none', 'important');
      a = a.parentElement;
    }
    hideOthers();
    document.documentElement.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('background', '#241F31', 'important');
    return true;
  }
  function start() {
    if (!apply()) return setTimeout(start, 500);
    // Keep hiding overlays added later (cookie/consent/privacy banners, modals).
    try {
      var mo = new MutationObserver(function () {
        if (!document.body.contains(target)) { if (!apply()) return; }
        else hideOthers();
      });
      mo.observe(document.body, { childList: true });
    } catch (e) {}
    setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 200);
  }
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', start);
  else start();
})();
""" % json.dumps(selector)
    return WebKit.UserScript.new(
        source,
        WebKit.UserContentInjectedFrames.TOP_FRAME,
        WebKit.UserScriptInjectionTime.END,
        None, None,
    )


def _hide_stylesheet(selectors) -> "WebKit.UserStyleSheet":
    css = ", ".join(selectors) + " { display: none !important; }"
    return WebKit.UserStyleSheet.new(
        css,
        WebKit.UserContentInjectedFrames.TOP_FRAME,
        WebKit.UserStyleLevel.USER,
        None, None,
    )


def build_page(network_session, url: str, *, isolate_selector: str = "",
               hide_selectors=()) -> "WebKit.WebView":
    view = make_webview(network_session)
    ucm = view.get_user_content_manager()
    from . import webfilter
    webfilter.apply_to(ucm)
    if isolate_selector:
        ucm.add_script(_isolation_script(isolate_selector))
    if hide_selectors:
        ucm.add_style_sheet(_hide_stylesheet(hide_selectors))
    view.load_uri(url)
    return view


class WebRuntime(Runtime):
    name = "web"
    embeds = True

    def build_view(self, title: Title, server: Server, network_session):
        return build_page(network_session, server.url,
                          isolate_selector=title.player_selector)
