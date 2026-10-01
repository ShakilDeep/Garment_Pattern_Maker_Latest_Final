"""P1-01 failure paths: every piece invariant rejects with a specific message."""

import pytest
from test_pattern_piece import P, _line, _outline, _piece, _points

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import Label, Notch
from app.domain.pattern.cutting import CutQuantity, FoldLine
from app.domain.pattern.ids import AnnotationId, SegmentId
from app.domain.pattern.point import PatternPoint

SQUARE = (_line("s1", "a", "b"), _line("s2", "b", "c"), _line("s3", "c", "d"), _line("s4", "d", "a"))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"outline": _outline()[:3]}, "not closed"),
        ({"outline": (_line("s1", "a", "b"), _line("s2", "c", "d"), _line("s4", "d", "a"))}, "not closed"),
        ({"outline": (_line("s1", "a", "b"), _line("s2", "b", "a"))}, "three straight"),
        (
            {"outline": (_line("s1", "a", "zz"), _line("s2", "zz", "c"), _line("s3", "c", "a"))},
            "Unknown point",
        ),
        (
            {"outline": (*SQUARE[:2], _line("s5", "c", "a"), _line("s6", "a", "d"), SQUARE[3])},
            "Duplicate outline",
        ),
        ({"points": (*_points(), PatternPoint(P["b"], Point2D(1, 1)))}, "Duplicate point id: b"),
        ({"points": (*_points()[:3], PatternPoint(P["d"], Point2D(20, 30)))}, "coincident"),
        ({"labels": (Label(AnnotationId("s1"), "Clash", Point2D(1, 1)),)}, "Duplicate piece element id: s1"),
        ({"notches": (Notch(AnnotationId("n9"), SegmentId("nope"), 0.5),)}, "not on an outline segment"),
        ({"fold": FoldLine(SegmentId("s2"))}, "straight outline segment"),
        ({"fold": None}, "exactly when"),
        ({"cut": CutQuantity(0, 1, 0)}, "exactly when"),
        ({"name": " "}, "name"),
        ({"name": None}, "name"),
        ({"cut": None}, "CutQuantity"),
        ({"grainline": "x"}, "grainline"),
        ({"id": "back"}, "PieceId"),
    ],
    ids=[
        "open-chain",
        "gap",
        "two-lines",
        "unknown-point",
        "revisited-vertex",
        "duplicate-point",
        "coincident",
        "id-clash",
        "stray-notch",
        "curved-fold",
        "fold-missing",
        "fold-unexpected",
        "blank-name",
        "none-name",
        "none-cut",
        "str-grainline",
        "str-id",
    ],
)
def test_piece_invariants_reject_invalid_pieces(changes, message):
    with pytest.raises(ValueError, match=message):
        _piece(**changes)
