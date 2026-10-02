"""Trim and extend (CAD-02): move one end of a straight line or outline edge along its own direction to where
it meets a boundary line (extended if need be). Trim must shorten the line and extend must lengthen it.
"""

from dataclasses import replace

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.construction import crossing, straight_ends
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Line
from app.domain.tolerances import COORDINATE

ENDS = ("start", "end")


def _fraction(anchor: Point2D, end: Point2D, reached: Point2D) -> float:
    """Where `reached` lies along anchor→end: 0 at the anchor, 1 at the current end."""
    span, offset = Vector2D.between(anchor, end), Vector2D.between(anchor, reached)
    return (span.x * offset.x + span.y * offset.y) / (span.length ** 2)


def _line_ends(piece: Piece, target: str, end: str) -> tuple[Point2D, Point2D]:
    """(anchor, end) of the target's last stretch at that end; outline edges must be straight."""
    for line in piece.internal_lines:
        if str(line.id) == target:
            points = line.points if end == "end" else line.points[::-1]
            return points[-2], points[-1]
    start, finish = straight_ends(piece, target)
    return (start, finish) if end == "end" else (finish, start)


def reach(piece: Piece, target: str, end: str, boundary: str, *, lengthen: bool) -> Piece:
    if end not in ENDS:
        raise ValueError("end must be 'start' or 'end'")
    anchor, current = _line_ends(piece, target, end)
    reached = crossing((anchor, current), straight_ends(piece, boundary))
    fraction = _fraction(anchor, current, reached)
    tolerance = COORDINATE / Vector2D.between(anchor, current).length
    if lengthen and fraction <= 1 + tolerance:
        raise ValueError(f"The boundary {boundary} does not lengthen {target} at its {end}")
    if not lengthen and not tolerance < fraction < 1 - tolerance:
        raise ValueError(f"The boundary {boundary} does not shorten {target} at its {end}")
    return _moved_end(piece, target, end, reached)


def _moved_end(piece: Piece, target: str, end: str, reached: Point2D) -> Piece:
    for line in piece.internal_lines:
        if str(line.id) == target:
            points = (*line.points[:-1], reached) if end == "end" else (reached, *line.points[1:])
            lines = tuple(replace(m, points=points) if m.id == line.id else m for m in piece.internal_lines)
            return replace(piece, internal_lines=lines)
    edge = next(s for s in piece.outline if str(s.id) == target and isinstance(s, Line))
    return piece.move_point(edge.end if end == "end" else edge.start, reached.x, reached.y)
