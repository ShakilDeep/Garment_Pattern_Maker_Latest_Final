"""T131: the cut-line corner of each outline point, where the grade point of a graded export sits."""
import pytest

from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.pattern.cut_corners import cut_corners
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance

SPEC = PieceSpec("p", "Panel", CutQuantity(1, 0, 0))


def _xy(corners, name):
    point = corners[PointId(name)]
    return point.x, point.y


def _square():
    return (PieceSketch().start("a", 0, 0).line_to("b", 10, 0).line_to("c", 10, 10).line_to("d", 0, 10)
            .close().build(SPEC))


def test_a_square_s_corners_are_its_mitres():
    corners = cut_corners(_square(), SeamAllowance(1.0))
    assert _xy(corners, "a") == pytest.approx((-1.0, -1.0)) and _xy(corners, "c") == pytest.approx((11, 11))


def test_unequal_widths_meet_where_both_cut_lines_cross():
    allowance = SeamAllowance(1.0, ((SegmentId("a:b"), 3.5), (SegmentId("d:a"), 0.8)))
    assert _xy(cut_corners(_square(), allowance), "a") == pytest.approx((-0.8, -3.5))


def test_a_corner_between_parallel_edges_is_the_point_beside_it():
    straight = (PieceSketch().start("a", 0, 0).line_to("m", 5, 0).line_to("b", 10, 0).line_to("c", 10, 10)
                .close().build(SPEC))
    assert _xy(cut_corners(straight, SeamAllowance(1.0)), "m") == pytest.approx((5, -1))


def test_a_clockwise_outline_offsets_to_its_own_outside():
    clockwise = (PieceSketch().start("a", 0, 0).line_to("d", 0, 10).line_to("c", 10, 10).line_to("b", 10, 0)
                 .close().build(SPEC))
    assert _xy(cut_corners(clockwise, SeamAllowance(1.0)), "a") == pytest.approx((-1.0, -1.0))
