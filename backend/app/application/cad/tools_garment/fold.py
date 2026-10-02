"""Fold and unfold tools (CAD-03); style-wide like the dart tools, with the seam allowance mirrored or trimmed."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_garment.params import piece_id
from app.application.cad.tools_modify.split_join import TopologyEdit
from app.domain.pattern.garment.allowance import followed
from app.domain.pattern.garment.fold import check_fold, fold
from app.domain.pattern.garment.outline_run import run_between
from app.domain.pattern.garment.unfold import unfold
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance


def unfold_piece(params: Params) -> TopologyEdit:
    """Mirror copies get ids ending in `suffix` (for example ".m")."""
    require_params(params, ("piece_id", "suffix"))
    suffix = text(params, "suffix")

    def follow(allowance: SeamAllowance, piece: Piece) -> SeamAllowance:
        if piece.fold is None:
            raise ValueError(f"{piece.name} has no fold edge to unfold")
        line = next(s for s in piece.outline if s.id == piece.fold.segment)
        half = run_between(piece, line.end, line.start)
        widths = {SegmentId(f"{s.id}{suffix}"): s.id for s in half}
        corners = {PointId(f"{s.end}{suffix}"): s.end for s in half[:-1]}
        return followed(allowance, widths, {line.id}, corners)

    return TopologyEdit(piece_id(params), lambda piece: unfold(piece, suffix), follow, "unfold_piece")


def fold_piece(params: Params) -> TopologyEdit:
    """Keep the outline from `start_id` forward to `end_id`; the fold edge `segment_id` runs back from end to start."""
    require_params(params, ("piece_id", "start_id", "end_id", "segment_id"))
    start, end = PointId(text(params, "start_id")), PointId(text(params, "end_id"))
    segment = SegmentId(text(params, "segment_id"))

    def follow(allowance: SeamAllowance, piece: Piece) -> SeamAllowance:
        check_fold(piece, start, end, segment)  # the same refusals as the edit itself, before reading the runs
        removed = run_between(piece, end, start)
        return followed(allowance, {}, {*(s.id for s in removed), *(s.end for s in removed[:-1])})

    return TopologyEdit(piece_id(params), lambda piece: fold(piece, start, end, segment), follow, "fold_piece")
