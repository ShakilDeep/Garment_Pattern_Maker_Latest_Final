"""P1-01 acceptance: ids are unique and the outline is a closed, simple chain of the piece's own points."""

from dataclasses import replace

import pytest

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import Label, Notch
from app.domain.pattern.cutting import CutQuantity, FoldLine, Grainline
from app.domain.pattern.ids import AnnotationId, PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Arc, CubicBezier, Line

CORNERS = {"a": (0, 0), "b": (20, 0), "c": (20, 30), "d": (0, 30)}
P = {k: PointId(k) for k in [*CORNERS, "zz"]}


def _points():
    return tuple(PatternPoint(P[k], Point2D(*v)) for k, v in CORNERS.items())


def _line(sid, start, end):
    return Line(SegmentId(sid), P[start], P[end])


def _outline():
    curve = CubicBezier(SegmentId("s2"), P["b"], P["c"], Vector2D(5, 10), Vector2D(5, -10))
    return (_line("s1", "a", "b"), curve, Arc(SegmentId("s3"), P["c"], P["d"], 0.4), _line("s4", "d", "a"))


def _piece(**changes):
    fields = {
        "id": PieceId("back"),
        "name": "Back",
        "points": _points(),
        "outline": _outline(),
        "cut": CutQuantity(0, 0, 1),
        "grainline": Grainline(Point2D(10, 5), Point2D(10, 25)),
        "fold": FoldLine(SegmentId("s4")),
        "notches": (Notch(AnnotationId("n1"), SegmentId("s2"), 0.5),),
        "labels": (Label(AnnotationId("l1"), "Back", Point2D(10, 15)),),
    }
    return Piece(**{**fields, **changes})


def test_mixed_segment_outline_builds_a_closed_hashable_piece():
    piece = _piece()
    assert [s.start for s in piece.outline] == [P[k] for k in "abcd"] and piece.cut.total == 1
    assert hash(piece) == hash(_piece())


def test_list_inputs_are_frozen_into_tuples():
    points, outline = list(_points()), list(_outline())
    piece = _piece(points=points, outline=outline)
    outline.pop()
    assert isinstance(piece.outline, tuple) and len(piece.outline) == 4 and hash(piece)


@pytest.mark.parametrize(
    "outline",
    [
        (_line("s1", "a", "b"), _line("s2", "b", "c"), _line("s3", "c", "a")),
        (Arc(SegmentId("s1"), P["a"], P["c"], 1.0), Arc(SegmentId("s2"), P["c"], P["a"], 1.0)),
    ],
    ids=["three-lines", "two-arcs"],
)
def test_minimal_outlines_are_accepted(outline):
    assert _piece(outline=outline, fold=None, cut=CutQuantity(1, 0, 0)).outline == outline


def test_moving_a_point_keeps_ids_and_carries_relative_handles():
    moved = _piece().move_point(P["c"], 22, 31)
    assert moved.point(P["c"]).position == Point2D(22, 31) and moved.outline == _piece().outline
    with pytest.raises(KeyError):
        moved.move_point(P["zz"], 0, 0)


def test_replace_revalidates():
    with pytest.raises(ValueError, match="closed"):
        replace(_piece(), outline=_outline()[:3])
