"""T130 / P1-11 (CAD-05): distance, edge and path length, corner angle, area and perimeter of V6 pieces."""
from dataclasses import replace
from math import sqrt

import pytest

from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.geom.curves import CubicBezier
from app.domain.geom.polyline_ops import length
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.measure import (
    angle_at,
    distance,
    edge_between,
    path_length,
    ring_area,
    ring_perimeter,
)
from app.domain.pattern.point import PatternPoint

SPEC = PieceSpec("p", "Panel", CutQuantity(1, 0, 0))


def _square():
    return (PieceSketch().start("a", 0, 0).line_to("b", 10, 0).line_to("c", 10, 10).line_to("d", 0, 10)
            .close().build(SPEC))


def _curved():
    return (PieceSketch().start("a", 0, 0).line_to("b", 10, 0)
            .curve_to("c", (10, 8), (Vector2D(0, 4), Vector2D(-3, 0))).close().build(SPEC))


def test_distance_between_two_points_of_a_piece():
    assert distance(_square(), PointId("a"), PointId("c")) == pytest.approx(sqrt(200))


def test_path_length_of_lines_and_a_cubic_to_within_a_hundredth():
    curve = CubicBezier(Point2D(10, 0), Point2D(10, 4), Point2D(7, 8), Point2D(10, 8))
    exact = length([(p.x, p.y) for p in curve.sample(65536)])
    piece = _curved()
    assert path_length(piece, [SegmentId("a:b")]) == pytest.approx(10)
    assert path_length(piece, [SegmentId("b:c")]) == pytest.approx(exact, abs=1e-5)
    assert path_length(piece, [SegmentId("a:b"), SegmentId("b:c")]) == pytest.approx(10 + exact, abs=1e-5)


def test_a_square_corner_is_ninety_degrees_and_a_smooth_join_is_one_eighty():
    assert angle_at(_square(), PointId("b")) == pytest.approx(90)
    smooth = (PieceSketch().start("a", 0, 0).line_to("b", 10, 0)
              .curve_to("c", (20, 5), (Vector2D(4, 0), Vector2D(-3, -3))).line_to("d", 0, 10).close().build(SPEC))
    assert angle_at(smooth, PointId("b")) == pytest.approx(180)


def test_area_and_perimeter_of_a_ring():
    ring = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
    assert (ring_area(ring), ring_perimeter(ring)) == (100, 40)


def test_edge_between_finds_any_piece_s_edge_by_its_end_points():
    assert str(edge_between(_square(), PointId("c"), PointId("d")).id) == "c:d"
    with pytest.raises(KeyError, match="Panel has no edge from d to b"):
        edge_between(_square(), PointId("d"), PointId("b"))


def test_unknown_ids_are_key_errors():
    with pytest.raises(KeyError, match="Panel has no point z"):
        distance(_square(), PointId("a"), PointId("z"))
    with pytest.raises(KeyError, match="Panel has no edge s9"):
        path_length(_square(), [SegmentId("s9")])
    with pytest.raises(ValueError, match="A path needs at least one edge"):
        path_length(_square(), [])


def test_an_angle_needs_an_outline_corner_not_a_construction_point():
    square = _square()
    marked = replace(square, points=(*square.points, PatternPoint(PointId("mid"), Point2D(5, 5))))
    with pytest.raises(ValueError, match="Panel: point mid is not a corner of the outline"):
        angle_at(marked, PointId("mid"))
