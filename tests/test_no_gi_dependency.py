"""Architectural guard: the tool/logic layer must not import the GTK stack.

The catalog validator and the core data logic have to run in CI and headless
environments without PyGObject. Each module below is imported in a *fresh*
interpreter; the test fails if importing it pulls in ``gi.repository`` (i.e.
someone added a top-level GTK import where it doesn't belong).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SRC = str(Path(__file__).resolve().parents[1] / "src")

GI_FREE_MODULES = [
    "yonderloft",
    "yonderloft.config",
    "yonderloft.models",
    "yonderloft.catalog_io",
    "yonderloft.profiles",
    "yonderloft.tools.validate_catalog",
]


@pytest.mark.parametrize("module", GI_FREE_MODULES)
def test_module_does_not_import_gtk(module):
    code = (
        f"import sys; sys.path.insert(0, {SRC!r}); "
        f"import {module}; "
        "import sys as _s; "
        "bad = [m for m in _s.modules if m == 'gi.repository' or m.startswith('gi.repository.')]; "
        "print(';'.join(bad))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        f"{module} imported GTK: {result.stdout.strip()}"
    )
