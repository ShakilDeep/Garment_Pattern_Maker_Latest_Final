"""Measure V6 pieces (CAD-05): point distance, edge and path length, corner angle, ring area and perimeter.

Lengths are in cm and angles in degrees. Curves are measured on a dense sampling (LENGTH_STEPS), not the
24-step display sampling: on the 1078375 armhole and sleeve cap the display polyline is 0.005-0.007 cm short
per curve, which seams of several curves would add into the 0.1 cm truing budget; at 2048 steps the
shortfall is below 1e-5 cm.
"""
from collections.abc import Sequence
from itertools import pairwise
from math import acos, degrees, hypot

from app.domain.geom.polyline_ops import length
from app.domain.geom.primitives import LineSegment, Point2D
from app.domain.pattern.edges import edge_tangents
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Segment

LENGTH_STEPS = 2048


def _position(piece: Piece, point_id: PointId) -> Point2D:
    found = next((p.position for p in piece.points if p.id == point_id), None)
    if found is None:
        raise KeyError(f"{piece.name} has no point {point_id}")
    return found


def distance(piece: Piece, start: PointId, end: PointId) -> float:
    a, b = _position(piece, start), _position(piece, end)
    return hypot(b.x - a.x, b.y - a.y)


def edge_between(piece: Piece, start: PointId, end: PointId) -> Segment:
    """The outline edge drawn from ``start`` to ``end`` (outline order); KeyError when there is none."""
    found = next((s for s in piece.outline if s.start == start and s.end == end), None)
    if found is None:
        raise KeyError(f"{piece.name} has no edge from {start} to {end}")
    return found


def segment_length(piece: Piece, segment: Segment, steps: int = LENGTH_STEPS) -> float:
    curve = resolve_segment(segment, {p.id: p.position for p in piece.points})
    if isinstance(curve, LineSegment):
        return float(curve.length)
    return length([(p.x, p.y) for p in curve.sample(steps)])


def path_length(piece: Piece, segment_ids: Sequence[SegmentId]) -> float:
    if not segment_ids:
        raise ValueError("A path needs at least one edge")
    by_id = {segment.id: segment for segment in piece.outline}
    missing = [str(i) for i in segment_ids if i not in by_id]
    if missing:
        raise KeyError(f"{piece.name} has no edge {missing[0]}")
    return sum(segment_length(piece, by_id[i]) for i in segment_ids)


def angle_at(piece: Piece, point_id: PointId) -> float:
    """The outline's inside angle at a point: 90 at a square corner, 180 where it runs on smoothly."""
    _position(piece, point_id)
    tangents = edge_tangents(piece)
    incoming = next((i for i, s in enumerate(piece.outline) if s.end == point_id), None)
    outgoing = next((i for i, s in enumerate(piece.outline) if s.start == point_id), None)
    if incoming is None or outgoing is None:
        raise ValueError(f"{piece.name}: point {point_id} is not a corner of the outline")
    back, ahead = tangents[incoming][1], tangents[outgoing][0]
    cosine = -(back.x * ahead.x + back.y * ahead.y)
    return degrees(acos(max(-1.0, min(1.0, cosine))))


def dense_ring(piece: Piece, steps: int = LENGTH_STEPS) -> tuple[Point2D, ...]:
    """The sew outline as an open ring with curves sampled densely, for area and perimeter."""
    positions = {p.id: p.position for p in piece.points}
    ring: list[Point2D] = []
    for segment in piece.outline:
        curve = resolve_segment(segment, positions)
        points = (curve.start, curve.end) if isinstance(curve, LineSegment) else curve.sample(steps)
        ring.extend(points[:-1])
    return tuple(ring)


def ring_area(ring: Sequence[Point2D]) -> float:
    return abs(sum(a.x * b.y - b.x * a.y for a, b in pairwise((*ring, ring[0])))) / 2


def ring_perimeter(ring: Sequence[Point2D]) -> float:
    return sum(hypot(b.x - a.x, b.y - a.y) for a, b in pairwise((*ring, ring[0])))
