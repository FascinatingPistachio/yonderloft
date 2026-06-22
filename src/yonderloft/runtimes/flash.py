"""``flash`` runtime: sandboxed legacy Pepper Flash for AS3 titles Ruffle can't
render yet.

This is the "use at your own risk" path from README §6. It is **not** part of
the v0.1 MVP — it lands in v0.2, where it runs confined inside the Flatpak
sandbox with the title's isolated profile and network scoped to its declared
domains. Until then it reports cleanly and points the user at the homepage.
"""
from __future__ import annotations

from ..models import Server, Title
from .base import Runtime, RuntimeNotReady


class FlashRuntime(Runtime):
    name = "flash"
    embeds = True
    legacy = True
    security_note = (
        "Legacy Flash runtime — unmaintained and unpatched. Runs sandboxed with "
        "an isolated profile, but don't reuse passwords here."
    )

    def build_view(self, title: Title, server: Server, network_session):
        raise RuntimeNotReady(
            "Sandboxed Flash isn't available yet — it's coming in v0.2 for the "
            "AS3 titles Ruffle can't render. For now, open this game in your "
            "browser instead.",
            homepage=title.homepage or server.url,
        )
