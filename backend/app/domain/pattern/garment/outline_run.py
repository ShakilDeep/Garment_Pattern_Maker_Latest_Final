"""Runs of a piece's outline (CAD-03): the segments from one outline point forward to another, cyclically."""

from collections.abc import Collection, Mapping

from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Segment


def edge(piece: Piece, segment_id: SegmentId) -> Segment:
    found = next((s for s in piece.outline if s.id == segment_id), None)
    if found is None:
        raise KeyError(f"Unknown edge {segment_id}")
    return found


def leaving(piece: Piece, point: PointId) -> int:
    """Index of the outline segment that starts at `point` (KeyError if unknown, ValueError if off the outline)."""
    piece.point(point)
    index = next((i for i, s in enumerate(piece.outline) if s.start == point), None)
    if index is None:
        raise ValueError(f"Point {point} is not on the outline")
    return index


def run_between(piece: Piece, first: PointId, last: PointId) -> tuple[Segment, ...]:
    """The segments from the one leaving `first` forward to the one arriving at `last`."""
    if first == last:
        raise ValueError(f"A run needs two different points, not {first} twice")
    count = len(piece.outline)
    start, end = leaving(piece, first), (leaving(piece, last) - 1) % count
    return tuple(piece.outline[(start + step) % count] for step in range((end - start) % count + 1))


def rebuilt(
    outline: tuple[Segment, ...], changes: Mapping[SegmentId, tuple[Segment, ...]], dropped: Collection[SegmentId]
) -> tuple[Segment, ...]:
    """The outline with some segments replaced (each by zero or more segments) and others removed."""
    return tuple(
        part for s in outline if s.id not in dropped for part in changes.get(s.id, (s,))
    )
