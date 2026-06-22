"""Process entry point. Sets up GI versions, gettext, then runs the app."""
from __future__ import annotations

import gettext
import locale
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Soup", "3.0")

from . import config


def _setup_i18n() -> None:
    try:
        locale.bindtextdomain("yonderloft", config.LOCALEDIR)
        locale.textdomain("yonderloft")
    except (AttributeError, locale.Error):
        pass
    gettext.bindtextdomain("yonderloft", config.LOCALEDIR)
    gettext.textdomain("yonderloft")
    gettext.install("yonderloft", config.LOCALEDIR)


def main() -> int:
    _setup_i18n()
    from .application import YonderloftApplication

    app = YonderloftApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
