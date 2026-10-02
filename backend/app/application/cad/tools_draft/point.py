"""Point tool (CAD-01): add a construction point to a piece; grading can target it by id (PM-02)."""

from dataclasses import dataclass, field, replace

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import PointId
from app.domain.pattern.point import PatternPoint, finite_point
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class AddPoint:
    target: PieceTarget
    point_id: PointId
    position: Point2D
    name: str = field(default="add_point", init=False)

    def apply(self, state: Style) -> Style:
        added = PatternPoint(self.point_id, self.position)
        return self.target.edit(state, lambda piece: replace(piece, points=(*piece.points, added)))


def add_point(params: Params) -> AddPoint:
    require_params(params, (*TARGET_PARAMS, "point_id", "x", "y"))
    position = finite_point(params["x"], params["y"])
    return AddPoint(PieceTarget.of(params), PointId(text(params, "point_id")), position)
