"""Shape tools (CAD-01): a rectangle or circle drafted as a new piece.

The piece is added to every size that has pieces, with the same geometry in each: it has no grade rules yet,
so nothing is derived for other sizes (P1-19 grading applies rules later). It gets no seam allowance until one
is set. Ids inside the piece are p0.., s0.. (unique within the piece, as for adapted V5 pieces).
"""

from dataclasses import dataclass

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import count, number, positive, text
from app.domain.geom.primitives import Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Arc, Line, Segment
from app.domain.pattern.style import Style

PIECE_PARAMS = ("piece_id", "name", "quantity")
HALF_CIRCLE_BULGE = 1.0  # tan(180° / 4)


@dataclass(frozen=True)
class AddShape:
    piece: Piece
    name: str

    def apply(self, state: Style) -> Style:
        return state.with_added_piece(self.piece)


def _piece(params: Params, corners: list[Point2D], segments: list[Segment]) -> Piece:
    points = tuple(PatternPoint(PointId(f"p{i}"), corner) for i, corner in enumerate(corners))
    cut = CutQuantity(count(params, "quantity"), 0, 0)
    return Piece(PieceId(text(params, "piece_id")), text(params, "name"), points, tuple(segments), cut)


def add_rectangle(params: Params) -> AddShape:
    require_params(params, (*PIECE_PARAMS, "x", "y", "width", "height"))
    x, y = number(params, "x"), number(params, "y")
    width, height = positive(params, "width"), positive(params, "height")
    corners = [Point2D(x, y), Point2D(x + width, y), Point2D(x + width, y + height), Point2D(x, y + height)]
    lines: list[Segment] = [
        Line(SegmentId(f"s{i}"), PointId(f"p{i}"), PointId(f"p{(i + 1) % 4}")) for i in range(4)
    ]
    return AddShape(_piece(params, corners, lines), "add_rectangle")


def add_circle(params: Params) -> AddShape:
    require_params(params, (*PIECE_PARAMS, "cx", "cy", "radius"))
    cx, cy, radius = number(params, "cx"), number(params, "cy"), positive(params, "radius")
    ends = [Point2D(cx + radius, cy), Point2D(cx - radius, cy)]
    arcs: list[Segment] = [
        Arc(SegmentId("s0"), PointId("p0"), PointId("p1"), HALF_CIRCLE_BULGE),
        Arc(SegmentId("s1"), PointId("p1"), PointId("p0"), HALF_CIRCLE_BULGE),
    ]
    return AddShape(_piece(params, ends, arcs), "add_circle")
