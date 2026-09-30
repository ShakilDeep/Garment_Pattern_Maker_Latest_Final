"""Angle tolerance boundaries for outline flattening and spike turns."""
from math import radians, tan

import pytest

from app.domain.tolerances import ANGLE_DEGREES
from app.infrastructure.outline_quality import outline_quality


@pytest.mark.parametrize(
    "side,flattening",
    [(-1, True), (0, True), (1, False)],
)
def test_flattening_includes_exact_angle_threshold(side, flattening):
    y = 5 * tan(radians(ANGLE_DEGREES + side * 0.01))
    piece = {
        "name": "Threshold",
        "points": [[0, 0], [5, 0], [10, y], [10, 6], [0, 6], [0, 0]],
    }
    issues = outline_quality({"pieces": [piece]})
    assert any(issue["code"] == "FLATTENING" for issue in issues) is flattening


@pytest.mark.parametrize(
    "side,spike",
    [(-1, True), (0, True), (1, False)],
)
def test_spike_turn_includes_exact_angle_threshold(side, spike):
    y = 10 * tan(radians(ANGLE_DEGREES + side * 0.01))
    piece = {
        "name": "Spike",
        "points": [[0, 0], [10, 0], [0, y], [0, 10], [6, 10], [0, 0]],
    }
    issues = outline_quality({"pieces": [piece]})
    assert any(issue["code"] == "TURN_ANGLE" for issue in issues) is spike
