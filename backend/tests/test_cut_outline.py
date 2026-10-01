"""P1-04: a per-edge seam allowance builds the cut outline around the stitch line (PM-03)."""

from math import hypot

import pytest
from test_pattern_piece import P, _piece

from app.domain.geom.primitives import Point2D
from app.domain.pattern.cut_outline import offset_ring
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.segment import Arc, Line
from app.domain.tolerances import LENGTH_CM

RECT = [(0, 0), (20, 0), (20, 30), (0, 30)]  # counter-clockwise: s0 bottom, s1 right, s2 top, s3 left


def polygon(coords):
    points = tuple(PatternPoint(PointId(f"p{i}"), Point2D(*xy)) for i, xy in enumerate(coords))
    count = len(points)
    lines = tuple(Line(SegmentId(f"s{i}"), points[i].id, points[(i + 1) % count].id) for i in range(count))
    return Piece(PieceId("shape"), "Shape", points, lines, CutQuantity(1, 0, 0))


def widths(*values):
    return tuple((SegmentId(f"s{i}"), float(w)) for i, w in enumerate(values))


def test_per_edge_widths_mitre_a_rectangle_exactly():
    cut = offset_ring(polygon(RECT), SeamAllowance(0, widths(4, 1, 2, 3)))
    assert cut == (Point2D(21, -4), Point2D(21, 32), Point2D(-3, 32), Point2D(-3, -4))


def test_clockwise_outlines_are_offset_outwards_too():
    cut = offset_ring(polygon(RECT[::-1]), SeamAllowance(1))
    assert {(p.x, p.y) for p in cut} == {(-1, -1), (21, -1), (21, 31), (-1, 31)}


def test_zero_allowance_returns_the_stitch_corners():
    assert offset_ring(polygon(RECT), SeamAllowance(0)) == tuple(Point2D(*xy) for xy in RECT[1:] + RECT[:1])


def test_curved_edges_are_offset_within_the_length_tolerance():
    points = (PatternPoint(P["a"], Point2D(0, 0)), PatternPoint(P["b"], Point2D(20, 0)))
    outline = (Line(SegmentId("s1"), P["a"], P["b"]), Arc(SegmentId("s2"), P["b"], P["a"], 1.0))
    dome = Piece(PieceId("dome"), "Dome", points, outline, CutQuantity(1, 0, 0))
    cut = offset_ring(dome, SeamAllowance(1))
    upper = [p for p in cut if p.y > 0]
    assert len(upper) > 10
    assert all(11 <= hypot(p.x - 10, p.y) + 1e-9 <= 11 + LENGTH_CM for p in upper)


def test_a_fold_edge_gets_no_allowance():
    cut = offset_ring(_piece(), SeamAllowance(1))
    assert min(p.x for p in cut) == 0 and Point2D(0, -1) in cut


@pytest.mark.parametrize(
    ("allowance", "message"),
    [
        (SeamAllowance(1, ((SegmentId("s4"), 0.5),)), "fold"),
        (SeamAllowance(1, ((SegmentId("nope"), 0.5),)), "unknown segment"),
        (SeamAllowance(1, corner_styles=((PointId("nope"), "mitre"),)), "unknown corner"),
    ],
    ids=["fold-width", "unknown-segment", "unknown-corner"],
)
def test_allowances_must_fit_the_piece(allowance, message):
    with pytest.raises(ValueError, match=message):
        offset_ring(_piece(), allowance)
