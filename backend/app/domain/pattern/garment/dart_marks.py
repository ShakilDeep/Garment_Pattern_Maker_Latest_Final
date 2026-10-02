"""Marks and a dart's V (CAD-03): the V between the legs is not fabric, so no mark may sit in or cross it.

A mark with a point strictly inside the V is refused by name, and so is an internal line whose segment
meets an edge of the V (it would run across the opening). Refusing is the only rule here; nothing is moved.
"""

from collections.abc import Sequence
from itertools import pairwise

from app.domain.geom.crossings import segments_meet
from app.domain.geom.primitives import Point2D
from app.domain.pattern.garment.region import inside
from app.domain.pattern.piece import Piece


def _marks(piece: Piece) -> list[tuple[str, tuple[Point2D, ...]]]:
    on_outline = {i for s in piece.outline for i in (s.start, s.end)}
    marks = [
        *((f"internal line {m.id}", m.points) for m in piece.internal_lines),
        *((f"drill hole {m.id}", (m.position,)) for m in piece.drills),
        *((f"label {m.id}", (m.position,)) for m in piece.labels),
        *((f"point {p.id}", (p.position,)) for p in piece.points if p.id not in on_outline),
    ]
    if piece.grainline is not None:
        marks.append(("the grainline", (piece.grainline.start, piece.grainline.end)))
    return marks


def refuse_in_dart(piece: Piece, corners: Sequence[Point2D], where: str) -> None:
    """Refuse any mark in or across the V with these corners (l1, apex, l2)."""
    edges = list(pairwise((*corners, corners[0])))
    for what, points in _marks(piece):
        if any(inside(p, corners) for p in points):
            raise ValueError(f"{what} lies inside {where}; move it first")
        if any(segments_meet(segment, edge) for segment in pairwise(points) for edge in edges):
            raise ValueError(f"{what} crosses {where}; move or split it first")
