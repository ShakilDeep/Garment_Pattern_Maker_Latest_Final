from math import nextafter

import pytest
from test_demo_goldens import values_for

from app.domain.drafting import draft
from app.domain.tolerances import (
    COORDINATE,
    LENGTH_CM,
    SLEEVE_EASE_CM,
    SOURCE_DIMENSION_CM,
)
from app.infrastructure.pattern_checks import structural_checks
from app.infrastructure.validation import validate


@pytest.mark.parametrize(
    "distance,expected", [(COORDINATE * 0.99, "PASS"), (COORDINATE, "PASS"), (COORDINATE * 1.01, "ERROR")]
)
def test_notch_distance_boundary(distance, expected):
    piece = {
        "name": "Rectangle",
        "points": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
        "notches": [[5, -distance]],
        "grainline": [[5, 2], [5, 8]],
    }
    issue = next(i for i in structural_checks({"pieces": [piece]}) if i["code"] == "NOTCHES")
    assert issue["severity"] == expected


@pytest.mark.parametrize(
    "distance,expected", [(COORDINATE * 0.99, "ERROR"), (COORDINATE, "ERROR"), (COORDINATE * 1.01, "PASS")]
)
def test_zero_edge_boundary(distance, expected):
    piece = {
        "name": "Rectangle",
        "points": [[0, 0], [distance, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
        "notches": [],
        "grainline": [[5, 2], [5, 8]],
    }
    issue = next(i for i in structural_checks({"pieces": [piece]}) if i["code"] == "EDGE_QUALITY")
    assert issue["severity"] == expected


@pytest.mark.parametrize(
    "tolerance,name", [(LENGTH_CM, "Yoke seam"), (SLEEVE_EASE_CM, "Sleeve cap / armhole")]
)
@pytest.mark.parametrize("side", [-1, 0, 1])
def test_seam_comparison_includes_exact_threshold(rows, tolerance, name, side):
    pattern = draft(values_for(rows, "L"), "L")
    pieces = {p["name"]: p for p in pattern["pieces"]}
    offset = tolerance + side * COORDINATE * 2
    if name == "Yoke seam":
        pieces["Back"]["seams"]["yoke"] = pieces["Yoke"]["seams"]["yoke"] + offset
    else:
        pieces["Sleeve"]["seams"]["cap"] = (
            pieces["Front"]["seams"]["armhole"] + pieces["Back"]["seams"]["armhole"] + offset
        )
    issue = next(i for i in validate(pattern) if i.get("name") == name)
    assert issue["severity"] == ("WARNING" if side > 0 else "PASS")


@pytest.mark.parametrize("side", [-1, 0, 1])
def test_source_dimension_boundary(rows, side):
    pattern = draft(values_for(rows, "L"), "L")
    cuff = next(p for p in pattern["pieces"] if p["name"] == "Cuff")
    cuff["width"] = pattern["measurements"]["cuff_edge_to_edge"] + SOURCE_DIMENSION_CM + side * COORDINATE * 2
    issue = next(
        i
        for i in validate(pattern)
        if i["code"] == "DIMENSION_CHECK" and i["message"].startswith("Cuff width")
    )
    assert issue["severity"] == ("WARNING" if side > 0 else "PASS")


def test_decimal_roundoff_does_not_fail_inclusive_seam_limit(rows):
    pattern = draft(values_for(rows, "L"), "L")
    by_name = {p["name"]: p for p in pattern["pieces"]}
    by_name["Yoke"]["seams"]["yoke"] = 48.5
    by_name["Back"]["seams"]["yoke"] = nextafter(48.5 + LENGTH_CM, float("inf"))
    issue = next(i for i in validate(pattern) if i.get("name") == "Yoke seam")
    assert issue["severity"] == "PASS"
