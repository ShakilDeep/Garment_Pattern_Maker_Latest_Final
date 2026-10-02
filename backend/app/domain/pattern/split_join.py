"""Split an outline edge in two, or join two edges back into one (CAD-02); notches keep their places.

The first part keeps the edge's id. A join only happens when the two edges continue one line, one circle
or one cubic (`subdivide.py`); anything else is refused rather than approximated.
"""

from dataclasses import replace

from app.domain.pattern.annotation import Notch
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.notch_position import point_on
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Segment
from app.domain.pattern.split_parts import joined_parts, split_parts


def _edge(piece: Piece, segment_id: SegmentId) -> Segment:
    segment = next((s for s in piece.outline if s.id == segment_id), None)
    if segment is None:
        raise KeyError(f"Unknown edge {segment_id}")
    if piece.fold is not None and piece.fold.segment == segment_id:
        raise ValueError(f"Edge {segment_id} is the fold line; it must stay one straight edge")
    return segment


def split_edge(piece: Piece, segment_id: SegmentId, t: float, point_id: PointId, new_id: SegmentId) -> Piece:
    if not 0 < t < 1:
        raise ValueError("t must be strictly between 0 and 1")
    segment = _edge(piece, segment_id)
    if any(p.id == point_id for p in piece.points):
        raise ValueError(f"Point id {point_id} is already used in {piece.name}")
    positions = {p.id: p.position for p in piece.points}
    at = point_on(resolve_segment(segment, positions), t)
    first, second = split_parts(segment, positions, t, point_id, new_id)
    outline = tuple(part for s in piece.outline for part in ((first, second) if s.id == segment_id else (s,)))
    notches = tuple(
        n if n.segment != segment_id
        else replace(n, t=n.t / t) if n.t <= t
        else Notch(n.id, new_id, (n.t - t) / (1 - t))
        for n in piece.notches
    )
    points = (*piece.points, PatternPoint(point_id, at))
    return replace(piece, points=points, outline=outline, notches=notches)


def join_at(piece: Piece, point_id: PointId) -> Piece:
    """Join the edge ending at `point_id` with the edge starting there, removing the point."""
    point = piece.point(point_id)
    if point.grade_rule is not None:
        raise ValueError(f"Point {point_id} has a grade rule; joining would remove it")
    first = next((s for s in piece.outline if s.end == point_id), None)
    second = next((s for s in piece.outline if s.start == point_id), None)
    if first is None or second is None:
        raise ValueError(f"Point {point_id} is not on the outline")
    _edge(piece, first.id)
    _edge(piece, second.id)
    joined, share = joined_parts(first, second, {p.id: p.position for p in piece.points})
    outline = tuple(joined if s.id == first.id else s for s in piece.outline if s.id != second.id)
    notches = tuple(
        replace(n, t=n.t * share) if n.segment == first.id
        else Notch(n.id, first.id, share + n.t * (1 - share)) if n.segment == second.id
        else n
        for n in piece.notches
    )
    points = tuple(p for p in piece.points if p.id != point_id)
    return replace(piece, points=points, outline=outline, notches=notches)

