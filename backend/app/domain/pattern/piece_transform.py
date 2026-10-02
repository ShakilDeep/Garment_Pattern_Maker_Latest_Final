"""Whole-piece transforms (CAD-02 move, rotate, mirror): one affine map applied to every part of the piece.

Points move; Bézier handles (offsets) take only the linear part; a mirror reverses every arc's turn (bulge
sign). Marks stored in absolute cm (internal lines, drill holes, labels and their direction, grainline) are
transformed too, as doc 108 requires for whole-piece edits. Notches and the fold are anchored by id.
"""

from dataclasses import replace
from math import atan2, degrees, radians

from app.domain.geom.lines import unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.cutting import Grainline
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Arc, CubicBezier, Segment
from app.domain.tolerances import COORDINATE


def rotation_about(center: Point2D, angle_degrees: float) -> Transform2D:
    turn = Transform2D.rotation(radians(angle_degrees))
    moved = turn.apply(center)
    return Transform2D(turn.a, turn.b, turn.c, turn.d, center.x - moved.x, center.y - moved.y)


def reflection(axis_start: Point2D, axis_end: Point2D) -> Transform2D:
    if Vector2D.between(axis_start, axis_end).length <= COORDINATE:
        raise ValueError("A mirror axis needs two distinct points")
    u = unit(Vector2D.between(axis_start, axis_end))
    a, b, d = u.x * u.x - u.y * u.y, 2 * u.x * u.y, u.y * u.y - u.x * u.x
    return Transform2D(a, b, b, d, axis_start.x - (a * axis_start.x + b * axis_start.y),
                       axis_start.y - (b * axis_start.x + d * axis_start.y))


def _vector(transform: Transform2D, vector: Vector2D) -> Vector2D:
    t = transform
    return Vector2D(t.a * vector.x + t.c * vector.y, t.b * vector.x + t.d * vector.y)


def transformed_segment(transform: Transform2D, segment: Segment, mirrored: bool) -> Segment:
    if isinstance(segment, CubicBezier):
        handles = _vector(transform, segment.start_handle), _vector(transform, segment.end_handle)
        return replace(segment, start_handle=handles[0], end_handle=handles[1])
    if isinstance(segment, Arc) and mirrored:
        return replace(segment, bulge=-segment.bulge)
    return segment


def label_direction(transform: Transform2D, angle_degrees: float, mirrored: bool) -> float:
    """A label's direction: turned by a rotation, reflected about a mirror axis (2φ = atan2(b, a))."""
    turn = degrees(atan2(transform.b, transform.a))
    return turn - angle_degrees if mirrored else angle_degrees + turn


def transformed(piece: Piece, transform: Transform2D) -> Piece:
    move = transform.apply
    mirrored = transform.a * transform.d - transform.b * transform.c < 0
    grain = piece.grainline
    return replace(
        piece,
        points=tuple(replace(p, position=move(p.position)) for p in piece.points),
        outline=tuple(transformed_segment(transform, s, mirrored) for s in piece.outline),
        internal_lines=tuple(replace(m, points=tuple(map(move, m.points))) for m in piece.internal_lines),
        drills=tuple(replace(m, position=move(m.position)) for m in piece.drills),
        labels=tuple(
            replace(m, position=move(m.position),
                    rotation_degrees=label_direction(transform, m.rotation_degrees, mirrored))
            for m in piece.labels
        ),
        grainline=None if grain is None else Grainline(move(grain.start), move(grain.end)),
    )
