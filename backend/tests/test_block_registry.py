"""T128: drafting goes through a block registry; the demo shirt block drafts exactly as before."""
import json

import pytest
from pom_workbooks import BOOK2

from app.domain.blocks.base import StyleOption
from app.domain.blocks.registry import BlockRegistry, demo_block, installed
from app.domain.blocks.run import draft_pattern
from app.domain.drafting import draft
from app.infrastructure.parsers import parse_xlsx


@pytest.fixture(scope="module")
def values():
    rows = parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx")
    return {size: {row["key"]: row["values"][size]["value"] for row in rows
                   if row["values"].get(size, {}).get("value") is not None and row["mapping_status"] != "unmapped"}
            for size in ("M", "L")}


def test_the_demo_shirt_is_installed_as_demo_v1():
    block = installed().get("demo_v1")
    assert (block.id, block.family, block.calibration) == ("demo_v1", "shirt", "demo")
    assert installed().ids("shirt") == ("demo_v1", "shirt_1078375", "shirt_v2")
    assert demo_block() is installed().get("shirt_v2")  # a new project drafts with the Optitex-shaped curves
    assert installed().ids("pant") == ()
    assert "half_chest" in block.required and all(option.fixed for option in block.options)


@pytest.mark.parametrize("size", ["M", "L"])
def test_drafting_through_the_registry_is_byte_identical(values, size):
    expected = draft(values[size], size, "demo_v1")
    actual = draft_pattern(installed().get("demo_v1"), values[size], size, {})
    assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def test_an_unknown_block_is_not_installed():
    with pytest.raises(ValueError, match="Drafting block is not installed: tee_v9"):
        installed().get("tee_v9")


class _Block:
    id, version, family, calibration = "x", "1", "shirt", "demo"
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    options = (StyleOption("yoke", "Yoke", ("split",), "split", fixed=True),)
    transforms = ()

    def draft(self, measurements, size, choices):
        return {"size": size}


def test_a_duplicate_block_id_is_rejected():
    registry = BlockRegistry()
    registry.register(_Block())
    with pytest.raises(ValueError, match="Block x is already registered"):
        registry.register(_Block())


def test_a_registry_without_a_demo_block_says_so():
    with pytest.raises(ValueError, match="No demo-calibration block is installed"):
        BlockRegistry().demo()
