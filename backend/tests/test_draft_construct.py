"""P1-08 (CAD-01): construction tools (offset, parallel, perpendicular, intersection)."""

import pytest
from test_cad_style_bus import BUS, _style
from test_draft_tools import ON_BACK, _back, _run

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import PointId


def test_offset_copies_an_edge_outside_or_inside_the_piece():
    outside = _back(_run("offset_edge", segment_id="s1", distance=1, line_id="o1")).internal_lines[-1]
    inside = _back(_run("offset_edge", segment_id="s1", distance=-1, line_id="o1")).internal_lines[-1]
    assert outside.points == (Point2D(0, -1), Point2D(20, -1))
    assert inside.points == (Point2D(0, 1), Point2D(20, 1))
    curve = _back(_run("offset_edge", segment_id="s3", distance=0.5, line_id="o2")).internal_lines[-1]
    assert len(curve.points) > 2 and max(p.y for p in curve.points) == pytest.approx(34.5, abs=0.02)
    with pytest.raises(ValueError, match="non-zero"):
        _run("offset_edge", segment_id="s1", distance=0, line_id="o1")


def test_parallel_moves_a_straight_edge_through_a_point():
    line = _back(_run("parallel_line", segment_id="s1", through=[5, 7], line_id="p1")).internal_lines[-1]
    assert line.points == (Point2D(0, 7), Point2D(20, 7))
    with pytest.raises(ValueError, match="straight"):
        _run("parallel_line", segment_id="s2", through=[5, 7], line_id="p1")


def test_perpendicular_drops_from_a_point_to_a_straight_edge():
    line = _back(_run("perpendicular_line", segment_id="s4", start=[8, 12], line_id="n2")).internal_lines[-1]
    assert line.points == (Point2D(8, 12), Point2D(0, 12))
    with pytest.raises(ValueError, match="already on"):
        _run("perpendicular_line", segment_id="s4", start=[0, 5], line_id="n2")


def test_intersection_marks_where_two_straight_lines_meet():
    style, history = BUS.dispatch(_style(), History(), "add_line", {**ON_BACK, "line_id": "v",
                                                                     "start": [7, 3], "end": [7, 9]})
    style, _ = BUS.dispatch(style, history, "intersection_point",
                            {**ON_BACK, "first": "s1", "second": "v", "point_id": "x1"})
    assert _back(style).point(PointId("x1")).position == Point2D(7, 0)
    with pytest.raises(ValueError, match="parallel"):
        _run("intersection_point", first="s1", second="s1", point_id="x1")
    with pytest.raises(ValueError, match="straight"):
        _run("intersection_point", first="s1", second="s3", point_id="x1")
