"""P1-04 Gate B round 2: outward curves meeting mitre/square corners, and fold-back's only-extend fallback."""

import pytest
from shapely.geometry import Polygon
from test_pattern_piece import P, _piece

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.segment import Arc, CubicBezier, Line
from app.infrastructure.piece_validity import check_cut_geometry


def _line(sid, start, end):
    return Line(SegmentId(sid), P[start], P[end])


def _rect_with(curve):
    outline = (_line("s1", "a", "b"), curve, _line("s3", "c", "d"), _line("s4", "d", "a"))
    return _piece(outline=outline, fold=None, cut=CutQuantity(1, 0, 0), notches=())


def _with_arc(coords, arc_index, bulge, name="X"):
    """A polygon piece whose edge arc_index is an arc with the given bulge; every other edge is a line."""
    points = tuple(PatternPoint(PointId(f"p{i}"), Point2D(*xy)) for i, xy in enumerate(coords))
    ids, count = [p.id for p in points], len(points)

    def edge(i):
        ends = (SegmentId(f"s{i}"), ids[i], ids[(i + 1) % count])
        return Arc(*ends, bulge) if i == arc_index else Line(*ends)

    return Piece(PieceId("x"), name, points, tuple(edge(i) for i in range(count)), CutQuantity(1, 0, 0))


def _valid(piece, allowance):
    cut = Polygon([(p.x, p.y) for p in check_cut_geometry(piece, allowance)])
    return cut.is_valid and cut.area > 0


@pytest.mark.parametrize("style", ["mitre", "square"])
@pytest.mark.parametrize("bulge", [0.2, 0.4])
@pytest.mark.parametrize("width", [1.0, 2.0])
def test_an_outward_arc_meeting_a_mitre_or_square_corner_is_accepted(style, bulge, width):
    piece = _rect_with(Arc(SegmentId("s2"), P["b"], P["c"], bulge))
    corners = tuple((PointId(k), style) for k in "abcd")
    assert _valid(piece, SeamAllowance(width, corner_styles=corners))


@pytest.mark.parametrize("handle", [(4, 8), (0, 8), (-4, 8)], ids=["outward", "straight", "inward"])
@pytest.mark.parametrize("width", [1.0, 2.0, 3.0])
def test_a_cubic_armhole_edge_is_accepted_at_every_width(handle, width):
    curve = CubicBezier(SegmentId("s2"), P["b"], P["c"], Vector2D(*handle), Vector2D(handle[0], -handle[1]))
    assert _valid(_rect_with(curve), SeamAllowance(width))


def test_fold_back_falls_back_to_the_mitre_rather_than_shorten_the_wider_edge():
    coords = [(-6.699, 8.699), (-8.063, 3.757), (-15.765, -2.55), (-10.803, -12.966), (-4.873, -14.982),
              (4.699, -8.923)]
    piece = _with_arc(coords, 2, 0.2)
    wide = ((SegmentId("s2"), 4.0),)
    styles = {s: SeamAllowance(1, wide, ((PointId("p2"), s),)) for s in ("fold_back", "mitre")}
    assert check_cut_geometry(piece, styles["fold_back"]) == check_cut_geometry(piece, styles["mitre"])


@pytest.mark.parametrize("size", [0.3, 0.5, 1.0])
@pytest.mark.parametrize("bulge", [-0.4, -0.2, 0.2, 0.4])
@pytest.mark.parametrize("width", [1.0, 2.0])
def test_a_small_rounded_corner_gets_a_valid_cut(size, bulge, width):
    piece = _with_arc([(0, 0), (20, 0), (20, 30), (size, 30), (0, 30 - size)], 3, bulge, "Rounded")
    assert _valid(piece, SeamAllowance(width))


def test_a_geometry_engine_failure_is_a_value_error_without_engine_details(monkeypatch, caplog):
    from shapely.errors import GEOSException

    import app.infrastructure.piece_validity as validity

    def broken(*_):
        raise GEOSException("TopologyException: side location conflict at 1 2")

    monkeypatch.setattr(validity, "envelope", broken)
    with pytest.raises(ValueError, match="could not be computed") as raised:
        check_cut_geometry(_rect_with(Arc(SegmentId("s2"), P["b"], P["c"], 0.4)), SeamAllowance(1))
    assert "Topology" not in str(raised.value) and "Topology" in caplog.text
