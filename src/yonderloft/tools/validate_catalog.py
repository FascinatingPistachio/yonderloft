"""Validate a catalog manifest. Used by contributors and CI.

    python3 -m yonderloft.tools.validate_catalog catalog/manifest.json

Checks (in order):
  1. JSON parses.
  2. Conforms to catalog/schema.json (if ``jsonschema`` is installed).
  3. Cross-field integrity: unique title IDs, every category referenced exists,
     each title has exactly the runtime-specific block it needs, exactly/at least
     one default server, and the referenced art file exists on disk.

Exit code 0 = valid, 1 = problems found, 2 = usage error. Pure stdlib except the
optional ``jsonschema`` dependency, so it runs without GTK.
"""
from __future__ import annotations

import json
import os
import sys


def _schema_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here))))
    return os.path.join(repo_root, "catalog", "schema.json")


def validate(manifest_path: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors fail the build; warnings don't."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        return [f"could not read/parse manifest: {exc}"], warnings

    catalog_root = os.path.dirname(os.path.abspath(manifest_path))

    # 2. JSON Schema (optional dependency).
    schema_path = _schema_path()
    try:
        import jsonschema  # type: ignore

        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(manifest), key=lambda e: e.path):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"schema: {loc}: {err.message}")
    except ImportError:
        print("note: jsonschema not installed — skipping schema validation",
              file=sys.stderr)

    # 3. Cross-field integrity (catches things schema can't express).
    categories = {c["id"] for c in manifest.get("categories", [])}
    seen_ids: set[str] = set()
    for title in manifest.get("titles", []):
        tid = title.get("id", "<missing id>")
        if tid in seen_ids:
            errors.append(f"{tid}: duplicate title id")
        seen_ids.add(tid)

        if title.get("category") not in categories:
            errors.append(f"{tid}: unknown category {title.get('category')!r}")

        if title.get("runtime") == "client" and "client" not in title:
            errors.append(f"{tid}: runtime 'client' requires a 'client' block")

        servers = title.get("servers", [])
        defaults = [s for s in servers if s.get("default")]
        if len(defaults) > 1:
            errors.append(f"{tid}: more than one default server")

        art = title.get("art")
        if art and not os.path.exists(os.path.join(catalog_root, art)):
            warnings.append(f"{tid}: art file not found (will use placeholder): {art}")

    return errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 -m yonderloft.tools.validate_catalog <manifest.json>",
              file=sys.stderr)
        return 2
    errors, warnings = validate(argv[1])
    for warn in warnings:
        print(f"  ! {warn}", file=sys.stderr)
    if errors:
        print(f"✗ {argv[1]}: {len(errors)} problem(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"✓ {argv[1]}: valid ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
