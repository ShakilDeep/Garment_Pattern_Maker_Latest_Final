"""T131: the sleeve cap is one smooth curve in every size; the crown notch only marks a point on it."""
import pytest

from app.domain.blocks.shirt.block import ShirtBlock
from app.domain.blocks.shirt.reference import graded_measurements, graded_sizes
from app.domain.pattern.ids import PointId
from app.domain.pattern.measure import angle_at

STRAIGHT_DEG = 180.0
KINK_DEG = 0.01


@pytest.mark.parametrize("size", graded_sizes())
def test_the_cap_runs_through_the_crown_without_a_kink(size):
    sleeve = next(p for p in ShirtBlock().draft_pieces(graded_measurements(size), size, {}) if str(p.id) == "Sleeve")
    assert angle_at(sleeve, PointId("cap_crown")) == pytest.approx(STRAIGHT_DEG, abs=KINK_DEG)


def test_corners_the_pds_draws_as_corners_stay_corners():
    sleeve = next(p for p in ShirtBlock().draft_pieces(graded_measurements("L"), "L", {}) if str(p.id) == "Sleeve")
    assert angle_at(sleeve, PointId("UA_front")) < STRAIGHT_DEG - 30  # a PDS turn point (>= 30 degrees)
