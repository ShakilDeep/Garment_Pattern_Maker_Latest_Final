"""Curve tool (CAD-01): turn an outline edge into a cubic Bézier with the given handles.

The edge keeps its id and end points, so notches stay anchored to it (PM-02). A fold edge must stay straight,
which the piece invariants enforce.
"""

from dataclasses import dataclass, field, replace

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import offset, text
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.domain.geom.primitives import Vector2D
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import CubicBezier
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class CurveEdge:
    target: PieceTarget
    segment_id: SegmentId
    start_handle: Vector2D
    end_handle: Vector2D
    name: str = field(default="curve_edge", init=False)

    def apply(self, state: Style) -> Style:
        return self.target.edit(state, self._curved)

    def _curved(self, piece: Piece) -> Piece:
        if self.segment_id not in {segment.id for segment in piece.outline}:
            raise KeyError(f"Unknown edge {self.segment_id}")
        outline = tuple(
            CubicBezier(s.id, s.start, s.end, self.start_handle, self.end_handle) if s.id == self.segment_id else s
            for s in piece.outline
        )
        return replace(piece, outline=outline)


def curve_edge(params: Params) -> CurveEdge:
    require_params(params, (*TARGET_PARAMS, "segment_id", "start_handle", "end_handle"))
    handles = offset(params, "start_handle"), offset(params, "end_handle")
    return CurveEdge(PieceTarget.of(params), SegmentId(text(params, "segment_id")), *handles)
