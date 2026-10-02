"""Smooth tool (CAD-02): make the outline tangent-continuous at a point (domain/pattern/smooth)."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.application.cad.tools_modify.piece_edit import PieceEdit
from app.domain.pattern.ids import PointId
from app.domain.pattern.smooth import smooth_at


def smooth_point(params: Params) -> PieceEdit:
    require_params(params, (*TARGET_PARAMS, "point_id"))
    point = PointId(text(params, "point_id"))
    return PieceEdit(PieceTarget.of(params), lambda piece: smooth_at(piece, point), "smooth_point")
