"""Move, rotate and mirror tools (CAD-02): the whole piece with its marks (domain/pattern/piece_transform)."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import number, xy
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.application.cad.tools_modify.piece_edit import PieceEdit
from app.domain.geom.transform import Transform2D
from app.domain.pattern.piece_transform import reflection, rotation_about, transformed


def _edit(params: Params, transform: Transform2D, name: str) -> PieceEdit:
    return PieceEdit(PieceTarget.of(params), lambda piece: transformed(piece, transform), name)


def move_piece(params: Params) -> PieceEdit:
    require_params(params, (*TARGET_PARAMS, "dx", "dy"))
    return _edit(params, Transform2D.translation(number(params, "dx"), number(params, "dy")), "move_piece")


def rotate_piece(params: Params) -> PieceEdit:
    """Counter-clockwise by `angle_degrees` about `center`."""
    require_params(params, (*TARGET_PARAMS, "angle_degrees", "center"))
    turn = rotation_about(xy(params, "center"), number(params, "angle_degrees"))
    return _edit(params, turn, "rotate_piece")


def mirror_piece(params: Params) -> PieceEdit:
    """Across the line through `axis_start` and `axis_end`."""
    require_params(params, (*TARGET_PARAMS, "axis_start", "axis_end"))
    return _edit(params, reflection(xy(params, "axis_start"), xy(params, "axis_end")), "mirror_piece")
