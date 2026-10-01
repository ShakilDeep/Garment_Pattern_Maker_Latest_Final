"""P1-01: pattern value objects (ids, points, segments, marks, cutting) validate on construction."""
from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label, Notch
from app.domain.pattern.cutting import CutQuantity, Grainline
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


@pytest.mark.parametrize("build", [
    lambda: finite_point(nan, 0), lambda: finite_point("1", 0), lambda: finite_point(True, 0),
    lambda: PatternPoint(A, Point2D(nan, 0)), lambda: CubicBezier(S, A, B, Vector2D(inf, 0), Vector2D(0, 0)),
    lambda: Arc(S, A, B, nan), lambda: Grainline(Point2D(nan, 0), Point2D(1, 1)),
    lambda: Label(N, "Front", Point2D(0, 0), nan), lambda: InternalLine(N, (Point2D(0, 0), Point2D(inf, 1))),
], ids=["factory-nan", "factory-str", "factory-bool", "point", "handle", "bulge", "grainline", "rotation",
        "internal-line"])
def test_constructors_reject_non_finite_values(build):
    with pytest.raises(ValueError, match="finite"):
        build()


@pytest.mark.parametrize("segment", [lambda: Line(S, A, A), lambda: Arc(S, A, A, 1.0),
                                     lambda: CubicBezier(S, A, A, Vector2D(1, 0), Vector2D(0, 1))])
def test_segments_need_distinct_end_points(segment):
    with pytest.raises(ValueError, match="distinct"):
        segment()


def test_straight_arc_is_rejected():
    with pytest.raises(ValueError, match="non-zero bulge"):
        Arc(S, A, B, 0)


@pytest.mark.parametrize(("single", "pairs", "fold", "total"), [(1, 0, 0, 1), (0, 1, 0, 2), (0, 0, 1, 1), (2, 1, 1, 5)])
def test_cut_quantity_totals(single, pairs, fold, total):
    assert CutQuantity(single, pairs, fold).total == total


@pytest.mark.parametrize("counts", [(0, 0, 0), (-1, 1, 0), (True, 0, 0), (1.5, 0, 0)])
def test_cut_quantity_rejects_empty_or_non_integer_counts(counts):
    with pytest.raises(ValueError, match="cut"):
        CutQuantity(*counts)


@pytest.mark.parametrize(("build", "message"), [
    (lambda: Grainline(Point2D(1, 1), Point2D(1, 1)), "grainline"),
    (lambda: DrillHole(N, Point2D(0, 0), 0), "diameter"), (lambda: DrillHole(N, Point2D(0, 0), True), "diameter"),
    (lambda: InternalLine(N, [Point2D(0, 0)]), "two points"), (lambda: Label(N, "  ", Point2D(0, 0)), "text"),
    (lambda: Notch(N, S, 1.5), "between 0 and 1"), (lambda: Notch(N, S, nan), "between 0 and 1"),
], ids=["grainline", "diameter-zero", "diameter-bool", "internal-line", "label", "notch-range", "notch-nan"])
def test_mark_shape_rules(build, message):
    with pytest.raises(ValueError, match=message):
        build()


def test_internal_line_coerces_a_list_to_a_tuple():
    line = InternalLine(N, [Point2D(0, 0), Point2D(1, 1)])
    assert isinstance(line.points, tuple) and hash(line)
