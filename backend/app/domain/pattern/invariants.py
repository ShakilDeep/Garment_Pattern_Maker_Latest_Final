"""Piece invariants (PM-01): unique ids, a closed simple outline of the piece's own points, anchored marks."""

from typing import TYPE_CHECKING

from app.domain.geom.primitives import Vector2D
from app.domain.pattern.cutting import CutQuantity, FoldLine, Grainline
from app.domain.pattern.ids import PieceId, require_unique
from app.domain.pattern.segment import Line
from app.domain.tolerances import COORDINATE

if TYPE_CHECKING:
    from app.domain.pattern.piece import Piece

MIN_SEGMENTS = 2
MIN_STRAIGHT_SEGMENTS = 3


def check_field_types(piece: "Piece") -> None:
    required = isinstance(piece.id, PieceId) and isinstance(piece.cut, CutQuantity)
    optional = all(
        value is None or isinstance(value, kind)
        for value, kind in ((piece.grainline, Grainline), (piece.fold, FoldLine))
    )
    if not (required and optional):
        raise ValueError("A piece needs a PieceId, a CutQuantity and typed grainline/fold values")


def check_ids(piece: "Piece") -> None:
    require_unique([p.id for p in piece.points], "point")
    marks = [*piece.outline, *piece.internal_lines, *piece.notches, *piece.drills, *piece.labels]
    require_unique([*(p.id for p in piece.points), *(m.id for m in marks)], "piece element")


def check_outline(piece: "Piece") -> None:
    outline = piece.outline
    if len(outline) < MIN_SEGMENTS or (
        all(isinstance(s, Line) for s in outline) and len(outline) < MIN_STRAIGHT_SEGMENTS
    ):
        raise ValueError(f"The outline of {piece.name} needs two curved or three straight segments")
    positions = {p.id: p.position for p in piece.points}
    unknown = sorted(str(i) for s in outline for i in (s.start, s.end) if i not in positions)
    if unknown:
        raise ValueError(f"Unknown point in the outline of {piece.name}: {unknown[0]}")
    for current, following in zip(outline, (*outline[1:], outline[0])):
        if current.end != following.start:
            raise ValueError(f"The outline of {piece.name} is not closed at segment {current.id}")
    require_unique([s.start for s in outline], "outline vertex")
    for segment in outline:
        if Vector2D.between(positions[segment.start], positions[segment.end]).length <= COORDINATE:
            raise ValueError(f"Segment {segment.id} of {piece.name} has coincident end points")


def check_marks(piece: "Piece") -> None:
    segments = {s.id: s for s in piece.outline}
    stray = [n.id for n in piece.notches if n.segment not in segments]
    if stray:
        raise ValueError(f"Notch {stray[0]} of {piece.name} is not on an outline segment")
    if piece.fold is not None and not isinstance(segments.get(piece.fold.segment), Line):
        raise ValueError(f"The fold of {piece.name} must be a straight outline segment")
    if (piece.fold is not None) != (piece.cut.on_fold > 0):
        raise ValueError(f"{piece.name} needs a fold edge exactly when it is cut on the fold")
