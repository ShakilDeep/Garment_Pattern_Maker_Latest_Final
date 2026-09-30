"""Yoke source-span DIMENSION_CHECK uses demo_v1 forward-shoulder, not raw SPTP."""
import pytest
from test_demo_goldens import values_for

from app.domain.back_yoke import back_shoulder_half
from app.domain.drafting import draft
from app.domain.tolerances import COORDINATE, SOURCE_DIMENSION_CM
from app.infrastructure.validation import validate


def _yoke_span_issue(pattern):
    return next(
        issue
        for issue in validate(pattern)
        if issue["code"] == "DIMENSION_CHECK" and issue["message"].startswith("Yoke shoulder span")
    )


def test_yoke_dimension_expected_is_forward_shoulder_span(rows):
    pattern = draft(values_for(rows, "L"), "L")
    measurements = pattern["measurements"]
    expected = 2 * back_shoulder_half(measurements["shoulder_point_to_point"] / 2, measurements)
    issue = _yoke_span_issue(pattern)
    assert issue["expected"] == pytest.approx(expected)
    assert issue["expected"] != pytest.approx(measurements["shoulder_point_to_point"])
    assert issue["severity"] == "PASS"
    assert "forward_shoulder_armhole" in issue["source_keys"]


def test_yoke_width_beyond_forward_shoulder_span_warns(rows):
    pattern = draft(values_for(rows, "L"), "L")
    measurements = pattern["measurements"]
    expected = 2 * back_shoulder_half(measurements["shoulder_point_to_point"] / 2, measurements)
    yoke = next(piece for piece in pattern["pieces"] if piece["name"] == "Yoke")
    yoke["width"] = expected + SOURCE_DIMENSION_CM + 2 * COORDINATE
    issue = _yoke_span_issue(pattern)
    assert issue["expected"] == pytest.approx(expected)
    assert issue["severity"] == "WARNING"
