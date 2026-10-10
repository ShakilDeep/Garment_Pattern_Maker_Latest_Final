"""Walk one seam along another (CAD-04): both lengths, their difference (the ease) and matching points.

A seam is one or more parts, each a run of outline edges through named points of one piece in outline order
(a sleeve cap; an armhole across front, back and yoke). With ``at_cm``, the point that far along each seam is
returned as (piece, edge, curve parameter t), where a notch pair can be placed.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from app.domain.geom.polyline_ops import length
from app.domain.geom.primitives import LineSegment
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.measure import LENGTH_STEPS, edge_between, segment_length
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Segment


@dataclass(frozen=True)
class WalkPart:
    piece_id: str
    points: tuple[str, ...]


@dataclass(frozen=True)
class Placement:
    piece_id: str
    segment: SegmentId
    t: float


@dataclass(frozen=True)
class WalkResult:
    first_cm: float
    second_cm: float
    difference_cm: float  # first - second: the ease the first seam carries
    at: tuple[Placement, Placement] | None


Edge = tuple[str, Piece, Segment, float]  # piece id, piece, edge, edge length


def _edges(pieces: Mapping[str, Piece], seam: Sequence[WalkPart]) -> list[Edge]:
    edges = []
    for part in seam:
        if part.piece_id not in pieces:
            raise KeyError(f"No piece {part.piece_id}")
        if len(part.points) < 2:
            raise ValueError("A walked seam needs at least two points")
        piece = pieces[part.piece_id]
        for start, end in pairwise(part.points):
            segment = edge_between(piece, PointId(start), PointId(end))
            edges.append((part.piece_id, piece, segment, segment_length(piece, segment)))
    return edges


def _parameter(piece: Piece, segment: Segment, distance: float, total: float) -> float:
    """The curve parameter t at arc length ``distance`` from the edge's start (dense sampling)."""
    curve = resolve_segment(segment, {p.id: p.position for p in piece.points})
    if isinstance(curve, LineSegment):
        return distance / total
    samples = curve.sample(LENGTH_STEPS)
    walked = 0.0
    for index in range(1, len(samples)):
        step = length([(samples[index - 1].x, samples[index - 1].y), (samples[index].x, samples[index].y)])
        if walked + step >= distance:
            return (index - 1 + (distance - walked) / step) / LENGTH_STEPS
        walked += step
    return 1.0


def _place(edges: list[Edge], at_cm: float) -> Placement:
    remaining = at_cm
    for piece_id, piece, segment, edge_length in edges:
        if remaining <= edge_length:
            return Placement(piece_id, segment.id, _parameter(piece, segment, remaining, edge_length))
        remaining -= edge_length
    raise ValueError(f"{at_cm} cm is past the end of the walked seam")


def walk(pieces: Mapping[str, Piece], first: Sequence[WalkPart], second: Sequence[WalkPart],
         at_cm: float | None = None) -> WalkResult:
    one, two = _edges(pieces, first), _edges(pieces, second)
    first_cm, second_cm = sum(e[3] for e in one), sum(e[3] for e in two)
    at = None if at_cm is None else (_place(one, at_cm), _place(two, at_cm))
    return WalkResult(first_cm, second_cm, first_cm - second_cm, at)
