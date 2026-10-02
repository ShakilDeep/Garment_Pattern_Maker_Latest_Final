"""Intersection tool (CAD-01): a construction point where two straight edges or lines (extended) meet."""

from dataclasses import dataclass, field, replace

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.domain.pattern.construction import crossing, straight_ends
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class IntersectionPoint:
    target: PieceTarget
    first: str
    second: str
    point_id: PointId
    name: str = field(default="intersection_point", init=False)

    def apply(self, state: Style) -> Style:
        return self.target.edit(state, self._marked)

    def _marked(self, piece: Piece) -> Piece:
        met = crossing(straight_ends(piece, self.first), straight_ends(piece, self.second))
        return replace(piece, points=(*piece.points, PatternPoint(self.point_id, met)))


def intersection_point(params: Params) -> IntersectionPoint:
    require_params(params, (*TARGET_PARAMS, "first", "second", "point_id"))
    return IntersectionPoint(
        PieceTarget.of(params), text(params, "first"), text(params, "second"), PointId(text(params, "point_id"))
    )
