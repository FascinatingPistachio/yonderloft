"""Tests against the real shipped catalog — the seed manifest must stay valid."""
from __future__ import annotations

import json

import pytest

from yonderloft import catalog_io
from yonderloft.models import Catalog, Runtime
from yonderloft.tools import validate_catalog


def test_real_manifest_parses_into_models(real_manifest):
    catalog = catalog_io.read_catalog(str(real_manifest))
    assert isinstance(catalog, Catalog)
    assert catalog.schema_version == 1
    assert len(catalog.titles) >= 10


def test_real_manifest_integrity_has_no_errors(real_manifest):
    errors, _warnings = validate_catalog.validate(str(real_manifest))
    assert errors == [], f"manifest has errors: {errors}"


def test_every_title_references_a_real_category(real_manifest):
    catalog = catalog_io.read_catalog(str(real_manifest))
    cat_ids = {c.id for c in catalog.categories}
    for title in catalog.titles:
        assert title.category in cat_ids, f"{title.id} -> {title.category}"


def test_every_title_has_exactly_one_default_server(real_manifest):
    catalog = catalog_io.read_catalog(str(real_manifest))
    for title in catalog.titles:
        defaults = [s for s in title.servers if s.default]
        assert len(defaults) == 1, f"{title.id} has {len(defaults)} defaults"


def test_client_titles_carry_a_client_block(real_manifest):
    catalog = catalog_io.read_catalog(str(real_manifest))
    for title in catalog.titles:
        if title.runtime is Runtime.CLIENT:
            assert title.client.get("source_url"), f"{title.id} missing client source"


def test_title_ids_are_unique(real_manifest):
    catalog = catalog_io.read_catalog(str(real_manifest))
    ids = [t.id for t in catalog.titles]
    assert len(ids) == len(set(ids))


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("jsonschema") is None,
    reason="jsonschema not installed",
)
def test_real_manifest_conforms_to_schema(real_manifest, real_schema):
    import jsonschema

    schema = json.loads(real_schema.read_text())
    manifest = json.loads(real_manifest.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(manifest))
    assert errors == [], [e.message for e in errors]
