"""Trim and extend tools (CAD-02): move one end of a straight line or edge to a boundary line."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.application.cad.tools_modify.piece_edit import PieceEdit
from app.domain.pattern.piece import Piece
from app.domain.pattern.reach import reach

REACH_PARAMS = (*TARGET_PARAMS, "target", "end", "boundary")


def _reach(params: Params, *, lengthen: bool, name: str) -> PieceEdit:
    require_params(params, REACH_PARAMS)
    target, end, boundary = text(params, "target"), text(params, "end"), text(params, "boundary")
    def change(piece: Piece) -> Piece:
        return reach(piece, target, end, boundary, lengthen=lengthen)

    return PieceEdit(PieceTarget.of(params), change, name)


def trim_line(params: Params) -> PieceEdit:
    return _reach(params, lengthen=False, name="trim_line")


def extend_line(params: Params) -> PieceEdit:
    return _reach(params, lengthen=True, name="extend_line")
