"""P1-03: export to V5 refuses pieces whose data a V5 dict cannot hold, instead of dropping or changing it."""

from dataclasses import replace

import pytest
from test_legacy_adapter_errors import _v5
from test_pattern_piece import _piece

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import AnnotationId, GradeRuleId, PointId
from app.domain.pattern.point import PatternPoint
from app.infrastructure.legacy_pattern_adapter import pattern_with_pieces, piece_from_v5, piece_to_v5
from app.infrastructure.legacy_piece import LegacyPiece

A = AnnotationId("m1")


def _square():
    return piece_from_v5(_v5()).piece


def _graded():
    first = _square().points[0]
    return replace(_square(), points=(replace(first, grade_rule=GradeRuleId("r1")), *_square().points[1:]))


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: _piece(), "fold edge"),
        (lambda: replace(_square(), cut=CutQuantity(0, 1, 0)), "mirrored pairs"),
        (lambda: _piece(fold=None, cut=CutQuantity(1, 0, 0)), "curved"),
        (lambda: replace(_square(), grainline=None), "grainline"),
        (lambda: replace(_square(), drills=(DrillHole(A, Point2D(5, 5), 0.4),)), "drill holes"),
        (lambda: replace(_square(), labels=(Label(A, "Front", Point2D(5, 5)),)), "labels"),
        (lambda: replace(_square(), internal_lines=(InternalLine(A, (Point2D(1, 1), Point2D(2, 2))),)), "internal"),
        (_graded, "grade rules"),
        (lambda: replace(_square(), points=(*_square().points, PatternPoint(PointId("c1"), Point2D(5, 5)))),
         "construction points"),
    ],
    ids=["fold", "pairs", "curved", "no-grainline", "drill", "label", "internal-line", "grade-rule", "loose-point"],
)
def test_pieces_v5_cannot_hold_are_refused(build, message):
    with pytest.raises(ValueError, match=message):
        piece_to_v5(LegacyPiece(build(), "{}"))


def test_every_reason_is_reported_at_once():
    piece = replace(_graded(), cut=CutQuantity(0, 1, 0))
    with pytest.raises(ValueError, match=r"mirrored pairs .*; grade rules"):
        piece_to_v5(LegacyPiece(piece, "{}"))


def test_pattern_pieces_must_match_the_pattern_ids_in_order():
    pattern = {"size": "M", "pieces": [_v5(id="a"), _v5(id="b")]}
    pieces = tuple(piece_from_v5(p) for p in pattern["pieces"])
    assert [p["id"] for p in pattern_with_pieces(pattern, pieces)["pieces"]] == ["a", "b"]
    with pytest.raises(ValueError, match="piece ids"):
        pattern_with_pieces(pattern, pieces[::-1])
