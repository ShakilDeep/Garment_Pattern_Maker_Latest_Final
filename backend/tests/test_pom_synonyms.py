"""T126 (M1): POM names map through a synonym table (data), after the buyer's exact codes."""
import pytest

from app.domain.catalog import MAPPING
from app.domain.pom_labels import is_half, normalize
from app.domain.pom_mapping import map_row
from app.domain.pom_synonyms import canonical_keys, check_unique, lookup


@pytest.mark.parametrize(("raw", "expected"), [
    (" ½ SEAT", "1/2 SEAT"),
    ("1/2 DRAWCORD LENGTH (FOLD TO END)-", "1/2 DRAWCORD LENGTH (FOLD TO END)"),
    ("*  ½ BICEP MESUREMENT", "1/2 BICEP MESUREMENT"),
    ("WAIS TEXT'D  MINUMUM AT TOP EDGE", "WAIS TEXT'D MINUMUM AT TOP EDGE"),
    ("1⁄2 waist", "1/2 WAIST"),
])
def test_names_are_normalized(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(("name", "half"), [
    ("1/2 WAIST AT TOP EDGE", True), (" LEG OPENING 1/2 (STRAIGHT )", True), ("HALF CHEST", True),
    ("HALF-CHEST", True), ("1/2-SEAT", True), (" INSEAM ( ALONG SM)", False), ("HALFWAY POINT", False),
    ("KNEE WIDTH 12\"", False),
])
def test_half_measurements_are_flagged_only_when_the_name_says_so(name, half):
    assert is_half(name) is half


def test_the_demo_codes_are_one_buyers_synonyms():
    assert len(MAPPING) == 35
    assert set(MAPPING.values()) <= set(canonical_keys())
    assert map_row("10225", "* 1/2 WAIST", None, set()) == ("half_waist", "catalog", "10225")


def test_names_and_alternative_names_map_through_the_synonym_table():
    assert lookup("1/2 WAIST AT TOP EDGE") == "half_waist"
    assert map_row("99", "unknown", "1/2 BASEN", set()) == ("half_seat", "synonym", "1/2 BASEN")
    assert lookup("Mystery") is None


def test_a_key_already_taken_by_an_earlier_row_is_not_reused():
    assert map_row("20305", " ½ SEAT", None, {"half_seat"}) == ("20305", "unmapped", None)


def test_one_name_may_not_point_at_two_keys():
    with pytest.raises(ValueError, match="Synonym 1/2 WAIST maps to both half_waist and other"):
        check_unique({"half_waist": ["1/2 waist"], "other": ["1/2 WAIST"]})
