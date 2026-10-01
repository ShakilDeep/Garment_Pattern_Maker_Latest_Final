"""P1-04 acceptance: cut outlines are Shapely-valid for all four corner styles; bad outlines are refused."""

import pytest
from shapely.geometry import Polygon
from test_corners import FLARED, L_SHAPE
from test_cut_outline import RECT, polygon
from test_demo_goldens import values_for
from test_pattern_piece import P, _piece

from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.segment import Arc
from app.infrastructure.legacy_pattern_adapter import draft_pieces
from app.infrastructure.piece_validity import check_cut_geometry

CURVED = _piece(fold=None, cut=CutQuantity(1, 0, 0))


def _every_corner(piece, style, width=1.0):
    return SeamAllowance(width, corner_styles=tuple((s.end, style) for s in piece.outline))


@pytest.mark.parametrize("style", list(CornerStyle))
@pytest.mark.parametrize("piece", [polygon(RECT), polygon(FLARED), polygon(L_SHAPE), CURVED, _piece()],
                         ids=["rect", "flared", "l-shape", "curved", "curved-fold"])
def test_cut_outline_is_valid_for_every_corner_style(piece, style):
    cut = Polygon([(p.x, p.y) for p in check_cut_geometry(piece, _every_corner(piece, style))])
    assert cut.is_valid and cut.area > 0


@pytest.mark.parametrize("style", list(CornerStyle))
def test_drafted_shirt_pieces_get_valid_cut_outlines(rows, style):
    for legacy in draft_pieces(values_for(rows, "L"), "L"):
        piece = legacy.piece
        stitch = Polygon([(p.position.x, p.position.y) for p in piece.points])
        cut = Polygon([(p.x, p.y) for p in check_cut_geometry(piece, _every_corner(piece, style))])
        assert cut.is_valid and cut.buffer(1e-6).contains(stitch), piece.name


@pytest.mark.parametrize(
    "piece",
    [
        polygon([(0, 0), (10, 0), (20, 0)]),
        _piece(outline=(Arc(SegmentId("s1"), P["a"], P["c"], 1.0),
                        Arc(SegmentId("s2"), P["c"], P["a"], -1.0)),
               fold=None, cut=CutQuantity(1, 0, 0)),
    ],
    ids=["collinear", "opposite-arcs"],
)
def test_zero_area_outlines_are_refused(piece):
    with pytest.raises(ValueError, match="zero area"):
        check_cut_geometry(piece, SeamAllowance(1))


def test_an_outline_that_revisits_a_position_is_refused():
    bow = polygon([(0, 0), (10, 0), (10, 10), (0, 10), (10, 0.0)])
    with pytest.raises(ValueError, match="not a simple outline"):
        check_cut_geometry(bow, SeamAllowance(1))


def test_a_slit_narrower_than_two_allowances_is_bridged_not_looped():
    slit = polygon([(0, 0), (10, 0), (10, 10), (5.2, 10), (5, 2), (4.8, 10), (0, 10)])
    cut = Polygon([(p.x, p.y) for p in check_cut_geometry(slit, SeamAllowance(1))])
    assert cut.is_valid and cut.contains(Polygon([(4.9, 9), (5.1, 9), (5.1, 10.5), (4.9, 10.5)]))
