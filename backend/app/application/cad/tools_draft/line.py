"""Line tool (CAD-01): add a straight internal line to a piece, in absolute cm (PM-01 marks)."""

from dataclasses import dataclass, field, replace
from itertools import pairwise

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text, xy
from app.application.cad.tools_draft.target import TARGET_PARAMS, PieceTarget
from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import InternalLine
from app.domain.pattern.ids import AnnotationId
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style


def with_line(piece: Piece, line_id: AnnotationId, points: tuple[Point2D, ...]) -> Piece:
    """The piece with one more internal line; the construction tools use it for the lines they compute."""
    line = InternalLine(line_id, points)
    if any(a == b for a, b in pairwise(line.points)):
        raise ValueError(f"Line {line_id} needs two distinct points in a row")
    return replace(piece, internal_lines=(*piece.internal_lines, line))


@dataclass(frozen=True)
class AddLine:
    target: PieceTarget
    line_id: AnnotationId
    start: Point2D
    end: Point2D
    name: str = field(default="add_line", init=False)

    def apply(self, state: Style) -> Style:
        return self.target.edit(state, lambda piece: with_line(piece, self.line_id, (self.start, self.end)))


def add_line(params: Params) -> AddLine:
    require_params(params, (*TARGET_PARAMS, "line_id", "start", "end"))
    return AddLine(PieceTarget.of(params), AnnotationId(text(params, "line_id")), xy(params, "start"),
                   xy(params, "end"))
