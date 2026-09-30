"""P0-02: oversized modules are split by responsibility while their import paths keep working."""
import importlib

import pytest

from app.domain import catalog
from app.infrastructure import exports, projections

SPLIT_HOMES = {
    "app.api.middleware": ("install_request_log",),
    "app.api.error_handlers": ("install_error_handlers",),
    "app.application.source_import": ("import_source", "clear_sources"),
    "app.infrastructure.export_svg": ("export_svg",),
    "app.infrastructure.export_pdf": ("export_pdf",),
    "app.domain.catalog_source_codes": ("MAPPING",),
    "app.infrastructure.projection_sql": ("encoded", "put"),
    "app.infrastructure.projection_sources": ("sync_sources",),
    "app.infrastructure.projection_patterns": ("sync_patterns",),
    "app.infrastructure.projection_workflow": ("sync_workflow",),
}


@pytest.mark.parametrize("module_name,names", sorted(SPLIT_HOMES.items()))
def test_split_modules_expose_their_responsibility(module_name, names):
    module = importlib.import_module(module_name)
    for name in names:
        assert hasattr(module, name), f"{module_name}.{name} missing"


def test_facades_keep_existing_import_paths():
    assert catalog.MAPPING is importlib.import_module("app.domain.catalog_source_codes").MAPPING
    assert projections.put is importlib.import_module("app.infrastructure.projection_sql").put
    assert exports.export_svg is importlib.import_module("app.infrastructure.export_svg").export_svg
    assert exports.export_pdf is importlib.import_module("app.infrastructure.export_pdf").export_pdf


def test_mapping_keeps_every_source_code_and_known_anchor():
    assert len(catalog.MAPPING) == 35
    assert catalog.MAPPING["10145-A"] == "half_chest"
