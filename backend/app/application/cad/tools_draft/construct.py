"""Construction tools (CAD-01) that draw an internal line from existing geometry: offset, parallel and
perpendicular. The geometry is computed when the command is applied, from that size's own piece.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.line import with_line
from app.application.cad.tools_draft.params import number, text, xy
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.domain.geom.primitives import Point2D
from app.domain.pattern.construction import foot_on_line, offset_edge, straight_ends, through_point
from app.domain.pattern.ids import AnnotationId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style

Construct = Callable[[Piece], tuple[Point2D, ...]]


@dataclass(frozen=True)
class ConstructLine:
    """Draw the line `construct` computes from the piece; `name` is the tool that built it."""

    target: PieceTarget
    line_id: AnnotationId
    construct: Construct
    name: str = field(default="construct_line", kw_only=True)

    def apply(self, state: Style) -> Style:
        return self.target.edit(state, lambda piece: with_line(piece, self.line_id, self.construct(piece)))


def _require(params: Params, extra: str) -> None:
    require_params(params, (*TARGET_PARAMS, "line_id", "segment_id", extra))


def _line(params: Params, name: str, construct: Construct) -> ConstructLine:
    return ConstructLine(PieceTarget.of(params), AnnotationId(text(params, "line_id")), construct, name=name)


def offset_line(params: Params) -> ConstructLine:
    """A copy of an edge `distance` cm outside the piece (negative: inside); curved edges follow their curve."""
    _require(params, "distance")
    segment, distance = SegmentId(text(params, "segment_id")), number(params, "distance")
    return _line(params, "offset_edge", lambda piece: offset_edge(piece, segment, distance))


def parallel_line(params: Params) -> ConstructLine:
    """A straight edge or line moved sideways, same length and direction, so it passes through a point."""
    _require(params, "through")
    reference, through = text(params, "segment_id"), xy(params, "through")
    return _line(params, "parallel_line", lambda piece: through_point(*straight_ends(piece, reference), through))


def perpendicular_line(params: Params) -> ConstructLine:
    """From a point to the foot of its perpendicular on a straight edge or line (extended if need be)."""
    _require(params, "start")
    reference, start = text(params, "segment_id"), xy(params, "start")
    return _line(params, "perpendicular_line",
                 lambda piece: (start, foot_on_line(start, *straight_ends(piece, reference))))
