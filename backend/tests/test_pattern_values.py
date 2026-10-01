"""P1-01: ids, points and segments validate on construction."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import InternalLine, Label
from app.domain.pattern.cutting import Grainline
from app.domain.pattern.ids import AnnotationId, GradeRuleId, PointId, SegmentId, require_unique
from app.domain.pattern.point import PatternPoint, finite_point
from app.domain.pattern.segment import Arc, CubicBezier, Line

A, B, S, N = PointId("a"), PointId("b"), SegmentId("s"), AnnotationId("n")


@pytest.mark.parametrize("value", ["p1", "front.neck:2", "A-9_x"])
def test_valid_ids(value):
    assert str(PointId(value)) == value


@pytest.mark.parametrize("value", ["", " p1", "p 1", "-lead", "x" * 65, 7])
def test_invalid_ids_are_rejected(value):
    with pytest.raises(ValueError, match="identifier"):
        PointId(value)


def test_duplicate_and_untyped_ids_are_rejected():
    with pytest.raises(ValueError, match="Duplicate point id: p2"):
        require_unique([PointId("p1"), PointId("p2"), PointId("p2")], "point")
    with pytest.raises(ValueError, match="must be an ElementId"):
        require_unique(["p1"], "point")


def test_moving_a_point_keeps_its_id_and_grade_rule():
    point = PatternPoint(PointId("hps"), finite_point(1, 2), GradeRuleId("rule-hps"))
    moved = point.moved_to(3.5, 4)
    assert (moved.id, moved.grade_rule, moved.position) == (point.id, point.grade_rule, Point2D(3.5, 4))
    with pytest.raises(FrozenInstanceError):
        point.id = PointId("other")  # type: ignore[misc]


@pytest.mark.parametrize(
    "build",
    [
        lambda: finite_point(nan, 0),
        lambda: finite_point("1", 0),
        lambda: finite_point(True, 0),
        lambda: PatternPoint(A, Point2D(nan, 0)),
        lambda: CubicBezier(S, A, B, Vector2D(inf, 0), Vector2D(0, 0)),
        lambda: Arc(S, A, B, nan),
        lambda: Grainline(Point2D(nan, 0), Point2D(1, 1)),
        lambda: Label(N, "Front", Point2D(0, 0), nan),
        lambda: InternalLine(N, (Point2D(0, 0), Point2D(inf, 1))),
    ],
    ids=[
        "factory-nan",
        "factory-str",
        "factory-bool",
        "point",
        "handle",
        "bulge",
        "grainline",
        "rotation",
        "internal-line",
    ],
)
def test_constructors_reject_non_finite_values(build):
    with pytest.raises(ValueError, match="finite"):
        build()


@pytest.mark.parametrize(
    "segment",
    [
        lambda: Line(S, A, A),
        lambda: Arc(S, A, A, 1.0),
        lambda: CubicBezier(S, A, A, Vector2D(1, 0), Vector2D(0, 1)),
    ],
)
def test_segments_need_distinct_end_points(segment):
    with pytest.raises(ValueError, match="distinct"):
        segment()


def test_arc_bulge_beyond_an_almost_full_circle_is_rejected():
    assert Arc(S, A, B, -1000).bulge == -1000
    with pytest.raises(ValueError, match="at most 1000"):
        Arc(S, A, B, 1e200)


def test_straight_arc_is_rejected():
    with pytest.raises(ValueError, match="non-zero bulge"):
        Arc(S, A, B, 0)
