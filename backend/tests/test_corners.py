"""P1-04: corner styles at the corner where edge A (in) meets edge B (out), as approved on 2026-10-02."""

import pytest
from test_cut_outline import RECT, polygon, widths

from app.domain.geom.lines import reflect
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.cut_outline import offset_ring
from app.domain.pattern.ids import PointId
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.piece_validity import check_cut_geometry

FLARED = [(0, 0), (40, 0), (34, 30), (6, 30)]  # hem s0 (A at p1), flared side s1 (B at p1)
L_SHAPE = [(0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20)]  # p3 is an inside corner
HEM, SIDE = 4.0, 1.0


def _cut(coords, style, corner="p1", allowance=None):
    widths_ = allowance or widths(HEM, *[SIDE] * (len(coords) - 1))
    return offset_ring(polygon(coords), SeamAllowance(0, widths_, ((PointId(corner), style),)))


def _distance_to_line(point, origin, direction):
    unit = Vector2D(direction.x / direction.length, direction.y / direction.length)
    return abs((point.x - origin.x) * unit.y - (point.y - origin.y) * unit.x)


def _side_cut_line():
    """B' on FLARED: the side p1 -> p2 moved outwards by SIDE."""
    side = Vector2D(-6, 30)
    normal = Vector2D(side.y / side.length * SIDE, -side.x / side.length * SIDE)
    return Point2D(40 + normal.x, normal.y), side


@pytest.mark.parametrize("style", list(CornerStyle))
def test_every_style_matches_the_mitre_on_a_square_corner(style):
    expected = Point2D(20 + SIDE, -HEM)
    assert expected in _cut(RECT, style)


def test_fold_back_mirrors_the_side_cut_line_across_the_hem_line():
    origin, side = _side_cut_line()
    hem_end = next(p for p in _cut(FLARED, CornerStyle.FOLD_BACK) if p.y == -HEM)
    mirrored = reflect(hem_end, Point2D(0, 0), Vector2D(1, 0))
    assert _distance_to_line(mirrored, origin, side) <= 1e-6
    on_both = [p for p in _cut(FLARED, "fold_back") if abs(p.y) <= 1e-9]
    assert any(_distance_to_line(p, origin, side) <= 1e-6 for p in on_both)


def test_reverse_mirrors_the_hem_cut_line_across_the_side_line():
    cut = _cut(FLARED, CornerStyle.REVERSE)
    on_side = [p for p in cut if _distance_to_line(p, *_side_cut_line()) <= 1e-6 and p.y < 30]
    mirrored = reflect(min(on_side, key=lambda p: p.y), Point2D(40, 0), Vector2D(-6, 30))
    assert abs(mirrored.y + HEM) <= 1e-6


def test_square_boxes_an_acute_corner_and_meets_at_an_obtuse_one():
    acute = _cut(FLARED, CornerStyle.SQUARE)
    assert Point2D(40 + SIDE, -HEM) in acute and Point2D(40 + SIDE, -HEM) not in _cut(FLARED, "mitre")
    assert _cut(FLARED, "square", corner="p2") == _cut(FLARED, "mitre", corner="p2")


@pytest.mark.parametrize("style", list(CornerStyle))
def test_inside_corners_are_trimmed_where_the_cut_lines_meet(style):
    allowance = SeamAllowance(1, corner_styles=((PointId("p3"), style),))
    assert _cut(L_SHAPE, style, "p3", widths(*[1] * 6)) == _cut(L_SHAPE, "mitre", "p3", widths(*[1] * 6))
    assert Point2D(11, 11) in check_cut_geometry(polygon(L_SHAPE), allowance)


def test_straight_continuations_step_between_unequal_widths():
    straight = [(0, 0), (10, 0), (20, 0), (20, 10), (0, 10)]
    cut = offset_ring(polygon(straight), SeamAllowance(1, widths(1, 3)))
    assert Point2D(10, -1) in cut and Point2D(10, -3) in cut
