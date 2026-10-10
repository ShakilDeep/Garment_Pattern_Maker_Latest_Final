"""Add notch (CAD-04): place a notch on an outline edge at curve parameter t, e.g. a pair found by walking."""
from dataclasses import replace

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import number, text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.application.cad.tools_modify.piece_edit import PieceEdit
from app.domain.pattern.annotation import Notch
from app.domain.pattern.ids import AnnotationId, SegmentId


def add_notch(params: Params) -> PieceEdit:
    require_params(params, (*TARGET_PARAMS, "notch_id", "segment", "t"))
    notch = Notch(AnnotationId(text(params, "notch_id")), SegmentId(text(params, "segment")), number(params, "t"))
    return PieceEdit(PieceTarget.of(params), lambda piece: replace(piece, notches=(*piece.notches, notch)), "add_notch")
