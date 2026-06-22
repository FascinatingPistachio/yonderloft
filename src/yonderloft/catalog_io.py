"""Pure (GTK-free) catalog parsing, local-fallback selection, and caching.

Kept separate from :mod:`yonderloft.catalog` — which owns the network fetch and
GObject signals — so this logic can be unit-tested without the GTK stack.
"""
from __future__ import annotations

import json
import os
from typing import Iterable, Optional

from .models import Catalog


def parse(raw: bytes | str) -> Catalog:
    """Parse manifest bytes/str into a :class:`Catalog` (raises on bad data)."""
    return Catalog.from_dict(json.loads(raw))


def read_catalog(path: str) -> Catalog:
    with open(path, "rb") as fh:
        return parse(fh.read())


def load_first_valid(paths: Iterable[tuple[str, str]]) -> tuple[Optional[Catalog], str]:
    """Return the first catalog that loads from ``(path, source_label)`` pairs.

    Tries each in order, skipping ones that are missing, unparseable, or use an
    unsupported schema. Returns ``(None, "")`` when none load.
    """
    for path, source in paths:
        try:
            return read_catalog(path), source
        except Exception:
            continue
    return None, ""


def write_cache(path: str, raw: bytes) -> None:
    """Atomically write the manifest cache (temp file + replace)."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(raw)
    os.replace(tmp, path)
