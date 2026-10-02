"""P1-09 (CAD-02): trim and extend move one end of a straight line or edge to a boundary line."""

import pytest
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style
from test_draft_tools import _back
from test_modify_transform import _run

from app.application.cad.history import History
from app.application.errors import GeometryInvalid
from app.domain.geom.primitives import Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style


def _with_line(style, line_id, start, end, piece="back"):
    params = {"size": "M", "piece_id": piece, "line_id": line_id, "start": start, "end": end}
    return BUS.dispatch(style, History(), "add_line", params)[0]


def test_extend_and_trim_an_internal_line_to_a_boundary():
    style = _with_line(_with_line(_style(), "h", [2, 10], [8, 10]), "wall", [15, 0], [15, 30])
    longer = _back(_run(style, "extend_line", target="h", end="end", boundary="wall")).internal_lines[0]
    assert longer.points == (Point2D(2, 10), Point2D(15, 10))
    cut = _with_line(style, "v5", [5, 0], [5, 30])
    trimmed = _back(_run(cut, "trim_line", target="h", end="start", boundary="v5")).internal_lines[0]
    assert trimmed.points == (Point2D(5, 10), Point2D(8, 10))


def test_extending_an_outline_edge_moves_its_end_point():
    style = _with_line(_style(), "far", [30, -10], [30, 40])
    extended = _back(_run(style, "extend_line", target="s1", end="end", boundary="far"))
    assert extended.point(PointId("b")).position == Point2D(30, 0)


@pytest.mark.parametrize(
    ("command", "end", "message"),
    [("trim_line", "end", "does not shorten"), ("extend_line", "start", "does not lengthen")],
)
def test_a_boundary_on_the_wrong_side_is_refused(command, end, message):
    style = _with_line(_with_line(_style(), "h", [2, 10], [8, 10]), "wall", [15, 0], [15, 30])
    with pytest.raises(ValueError, match=message):
        _run(style, command, target="h", end=end, boundary="wall")


def test_an_extension_that_makes_the_outline_cross_itself_is_blocked_with_a_message():
    corners = [(0, 0), (20, 0), (20, 5), (5, 5), (5, 20), (0, 20)]
    points = tuple(PatternPoint(PointId(f"p{i}"), Point2D(*xy)) for i, xy in enumerate(corners))
    outline = tuple(Line(SegmentId(f"s{i}"), PointId(f"p{i}"), PointId(f"p{(i + 1) % 6}")) for i in range(6))
    piece = Piece(PieceId("ell"), "Ell", points, outline, CutQuantity(1, 0, 0))
    before = _with_line(Style(StyleId("ell"), "Ell", ("M",), "M", {"M": SizePieces.from_pieces((piece,))}),
                        "left", [-10, -5], [-10, 30], piece="ell")
    params = {"size": "M", "piece_id": "ell", "target": "s2", "end": "end", "boundary": "left"}
    after = BUS.dispatch(before, History(), "extend_line", params)[0]
    with pytest.raises(GeometryInvalid) as caught:
        GUARD.check(before, after)
    assert "Self-intersection" in caught.value.details[0]["message"]
