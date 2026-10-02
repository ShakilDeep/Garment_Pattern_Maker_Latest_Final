"""Mirror images across a straight axis, used by fold and unfold (CAD-03).

A mirrored outline segment runs the other way: its ends swap, a Bézier's handles swap and reflect, and an
arc keeps its bulge (reversing and mirroring each flip its turn).
"""

from collections.abc import Callable
from dataclasses import replace

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.segment import CubicBezier, Segment

Rename = Callable[[PointId], PointId]


def reflected_vector(axis: Transform2D, vector: Vector2D) -> Vector2D:
    return Vector2D(axis.a * vector.x + axis.c * vector.y, axis.b * vector.x + axis.d * vector.y)


def mirrored_segment(axis: Transform2D, segment: Segment, rename: Rename, suffix: str) -> Segment:
    ident, start, end = SegmentId(f"{segment.id}{suffix}"), rename(segment.end), rename(segment.start)
    if isinstance(segment, CubicBezier):
        handles = reflected_vector(axis, segment.end_handle), reflected_vector(axis, segment.start_handle)
        return CubicBezier(ident, start, end, *handles)
    return replace(segment, id=ident, start=start, end=end)


def same_points(first: tuple[Point2D, ...], second: tuple[Point2D, ...], tolerance: float) -> bool:
    return len(first) == len(second) and all(
        Vector2D.between(p, q).length <= tolerance for p, q in zip(first, second)
    )
