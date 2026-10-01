"""P1-04 Gate B regressions: shallow bends, scalloped hems, needles, curve tangents and obtuse squares."""

from math import cos, radians, sin

import pytest
from shapely.geometry import Point, Polygon
from test_cut_outline import polygon, widths

from app.domain.geom.primitives import Point2D
from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.cut_outline import offset_ring
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.edges import stitch_ring
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.segment import Arc, Line
from app.infrastructure.piece_validity import check_cut_geometry


def _scalloped(count, bulge):
    hem = [Point2D(2 * i, 0) for i in range(count + 1)]
    corners = [Point2D(2 * count, 10), Point2D(0, 10)]
    points = tuple(PatternPoint(PointId(f"p{i}"), at) for i, at in enumerate([*hem, *corners]))
    ids = [p.id for p in points]
    arcs = [Arc(SegmentId(f"a{i}"), ids[i], ids[i + 1], bulge) for i in range(count)]
    tail = [Line(SegmentId(f"l{k}"), ids[count + k], ids[(count + k + 1) % len(ids)]) for k in range(3)]
    return Piece(PieceId("hem"), "Hem", points, (*arcs, *tail), CutQuantity(1, 0, 0))


@pytest.mark.parametrize(("count", "bulge"), [(2, 0.9), (2, 0.5), (12, 0.9), (12, 0.5)])
@pytest.mark.parametrize("width", [0.3, 1.0, 3.0])
def test_scalloped_hems_keep_their_full_allowance(count, bulge, width):
    piece = _scalloped(count, bulge)
    cut = Polygon([(p.x, p.y) for p in check_cut_geometry(piece, SeamAllowance(width))])
    stitch = Polygon([(p.x, p.y) for p in stitch_ring(piece)])
    reference = stitch.buffer(width, join_style="mitre", mitre_limit=1e9)
    assert cut.is_valid and cut.symmetric_difference(reference).area / reference.area < 1e-3


@pytest.mark.parametrize("bend", [1, 5, 10, 45])
def test_a_shallow_bend_with_unequal_widths_keeps_the_wider_band(bend):
    turn = radians(bend)
    far = (10 + 20 * cos(turn), 20 * sin(turn))
    piece = polygon([(0, 0), (10, 0), far, (far[0], far[1] + 10), (0, 10)])
    cut = Polygon([(p.x, p.y) for p in check_cut_geometry(piece, SeamAllowance(1, widths(1, 2)))])
    middle = (10 + 10 * cos(turn) + 2 * sin(turn) * 0.999, 10 * sin(turn) - 2 * cos(turn) * 0.999)
    assert cut.covers(Point(middle))


def test_a_needle_point_is_refused():
    with pytest.raises(ValueError, match="needle"):
        check_cut_geometry(polygon([(0, 0), (100, 0.04), (0, 0.08)]), SeamAllowance(1))


def test_corners_join_curves_at_their_true_tangent():
    points = (PatternPoint(PointId("a"), Point2D(0, 0)), PatternPoint(PointId("b"), Point2D(20, 0)))
    a, b = points[0].id, points[1].id
    outline = (Line(SegmentId("s1"), a, b), Arc(SegmentId("s2"), b, a, 1))
    dome = Piece(PieceId("dome"), "Dome", points, outline, CutQuantity(1, 0, 0))
    assert Point2D(21, -1) in offset_ring(dome, SeamAllowance(1))


def test_square_meets_as_a_mitre_at_an_obtuse_corner_with_unequal_widths():
    obtuse = [(0, 0), (40, 0), (46, 30), (-6, 30)]
    styles = {s: SeamAllowance(1, widths(4, 1), ((PointId("p1"), s),)) for s in ("square", "mitre")}
    assert offset_ring(polygon(obtuse), styles["square"]) == offset_ring(polygon(obtuse), styles["mitre"])


@pytest.mark.parametrize("style", list(CornerStyle))
def test_cw_outlines_mirror_ccw_ones_for_every_style(style):
    flared = [(0, 0), (40, 0), (34, 30), (6, 30)]
    mirrored = [(-x, y) for x, y in flared]
    allowance = SeamAllowance(1, widths(4, 1, 1, 1), ((PointId("p1"), style),))
    ccw = {(p.x, p.y) for p in check_cut_geometry(polygon(flared), allowance)}
    cw = {(-p.x, p.y) for p in check_cut_geometry(polygon(mirrored), allowance)}
    assert ccw == cw
