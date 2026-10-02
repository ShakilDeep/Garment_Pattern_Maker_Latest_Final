"""Split and join tools (CAD-02). They change a piece's edges, so they apply to every size that has pieces:
segment and point ids stay the same across sizes (grading and the per-piece seam allowance rely on that),
and the seam allowance follows the edges so the cut line does not change (domain allowance_topology).
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import number, text
from app.domain.pattern.allowance_topology import after_join, after_split
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.split_join import join_at, split_edge
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class TopologyEdit:
    piece_id: PieceId
    change: Callable[[Piece], Piece]
    follow: Callable[[SeamAllowance, Piece], SeamAllowance]  # given the base size's piece before the edit
    name: str

    def apply(self, state: Style) -> Style:
        if self.piece_id not in state.piece_ids:
            raise KeyError(f"Unknown piece {self.piece_id}")
        allowance = state.allowances.get(self.piece_id)
        base = next(p for p in state.view(state.base_size) if p.id == self.piece_id)
        followed = None if allowance is None else self.follow(allowance, base)
        style = state
        for size in state.geometry:
            piece = next(p for p in style.view(size) if p.id == self.piece_id)
            try:
                style = style.with_piece(size, self.change(piece))
            except ValueError as exc:
                raise ValueError(f"Size {size}: {exc}") from exc
        return style if followed is None else style.with_allowance(self.piece_id, followed)


def split_edge_tool(params: Params) -> TopologyEdit:
    """t is the edge's own parameter: a fraction of a line or arc, the curve parameter of a Bézier."""
    require_params(params, ("piece_id", "segment_id", "t", "point_id", "new_segment_id"))
    segment, t = SegmentId(text(params, "segment_id")), number(params, "t")
    point, new_segment = PointId(text(params, "point_id")), SegmentId(text(params, "new_segment_id"))
    return TopologyEdit(PieceId(text(params, "piece_id")),
                        lambda piece: split_edge(piece, segment, t, point, new_segment),
                        lambda allowance, _piece: after_split(allowance, segment, new_segment), "split_edge")


def join_edges(params: Params) -> TopologyEdit:
    require_params(params, ("piece_id", "point_id"))
    piece_id, point = PieceId(text(params, "piece_id")), PointId(text(params, "point_id"))

    def follow(allowance: SeamAllowance, piece: Piece) -> SeamAllowance:
        piece.point(point)  # an unknown point is a KeyError (404) whether or not the piece has an allowance
        first = next((s for s in piece.outline if s.end == point), None)
        second = next((s for s in piece.outline if s.start == point), None)
        if first is None or second is None:
            raise ValueError(f"Point {point} is not on the outline")
        return after_join(allowance, first.id, second.id, point)

    return TopologyEdit(piece_id, lambda piece: join_at(piece, point), follow, "join_edges")
