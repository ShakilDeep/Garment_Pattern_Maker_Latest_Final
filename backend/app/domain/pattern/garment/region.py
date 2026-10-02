"""Which marks travel with the turned or shifted part of a piece (CAD-03).

The moved part is a polygon: its run of outline closed across the slash (through the apex for a dart). A
mark wholly inside moves, one wholly outside stays, and one with points on both sides is refused by name
rather than cut or guessed. A point within COORDINATE of the polygon's boundary decides nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import pairwise

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label
from app.domain.pattern.cutting import Grainline
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_transform import label_direction
from app.domain.tolerances import COORDINATE


def segment_distance(point: Point2D, a: Point2D, b: Point2D) -> float:
    along, offset = Vector2D.between(a, b), Vector2D.between(a, point)
    squared = along.x * along.x + along.y * along.y
    share = 0.0 if squared == 0 else max(0.0, min(1.0, (offset.x * along.x + offset.y * along.y) / squared))
    return Vector2D.between(Point2D(a.x + share * along.x, a.y + share * along.y), point).length


def inside(point: Point2D, polygon: Sequence[Point2D]) -> bool | None:
    edges = list(pairwise((*polygon, polygon[0])))
    if any(segment_distance(point, a, b) <= COORDINATE for a, b in edges):
        return None
    crossings = sum(
        1 for a, b in edges
        if (a.y > point.y) != (b.y > point.y) and point.x < a.x + (point.y - a.y) * (b.x - a.x) / (b.y - a.y)
    )
    return crossings % 2 == 1


def moves(points: Sequence[Point2D], polygon: Sequence[Point2D], what: str) -> bool:
    sides = {side for side in (inside(p, polygon) for p in points) if side is not None}
    if len(sides) > 1:
        raise ValueError(f"{what} crosses the slash; move or split it first")
    return sides == {True}


@dataclass(frozen=True)
class Carried:
    """A piece's marks after the move, and the new positions of its construction points."""

    points: dict[PointId, Point2D]
    internal_lines: tuple[InternalLine, ...]
    drills: tuple[DrillHole, ...]
    labels: tuple[Label, ...]
    grainline: Grainline | None


def carried(piece: Piece, polygon: Sequence[Point2D], transform: Transform2D) -> Carried:
    move = transform.apply
    on_outline = {i for s in piece.outline for i in (s.start, s.end)}
    points = {
        p.id: move(p.position) for p in piece.points
        if p.id not in on_outline and moves((p.position,), polygon, f"point {p.id}")
    }
    lines = tuple(
        replace(m, points=tuple(map(move, m.points))) if moves(m.points, polygon, f"internal line {m.id}") else m
        for m in piece.internal_lines
    )
    drills = tuple(
        replace(m, position=move(m.position)) if moves((m.position,), polygon, f"drill hole {m.id}") else m
        for m in piece.drills
    )
    labels = tuple(
        replace(m, position=move(m.position), rotation_degrees=label_direction(transform, m.rotation_degrees, False))
        if moves((m.position,), polygon, f"label {m.id}") else m
        for m in piece.labels
    )
    grain = piece.grainline
    if grain is not None and moves((grain.start, grain.end), polygon, "the grainline"):
        grain = Grainline(move(grain.start), move(grain.end))
    return Carried(points, lines, drills, labels, grain)
