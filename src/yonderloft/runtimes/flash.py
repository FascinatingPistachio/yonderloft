"""``flash`` runtime: AS3 titles, played through Ruffle.

Per the project's decision, there is no bundled Adobe Flash — it's EOL and
proprietary, can't be shipped (Flathub bans it), and WebKitGTK can't host PPAPI
plugins anyway. Ruffle is the only Flash that ships: it's embedded and sandboxed
(Rust/WASM). The ``flash`` runtime therefore *is* Ruffle, kept as a separate
runtime only so the UI can be honest that AS3 coverage is still incomplete and
offer the browser as a fallback when a title doesn't render.
"""
from __future__ import annotations

from .ruffle import RuffleRuntime


class FlashRuntime(RuffleRuntime):
    name = "flash"
    embeds = True
    legacy = False
    security_note = (
        "Played through Ruffle (open-source, sandboxed). AS3 coverage is still "
        "improving — if this title doesn't load, use “Open in browser”."
    )
