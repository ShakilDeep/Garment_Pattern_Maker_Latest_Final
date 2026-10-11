"""Open a piece drawn as a half on the fold into the whole piece V5 views expect (T141b).

The drawn ring runs along the fold edge once; the whole piece is that ring without the fold edge plus its
mirror image across the fold line. Points on the fold line are not doubled.
"""
from collections.abc import Sequence

from app.domain.geom.lines import reflect
from app.domain.geom.primitives import Point2D, Vector2D

ON_FOLD_CM = 1e-4  # a point this close to the fold line lies on it


def _distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    axis = Vector2D.between(start, end)
    offset = Vector2D.between(start, point)
    return abs(axis.x * offset.y - axis.y * offset.x) / axis.length


def _fold_edge(ring: Sequence[Point2D], start: Point2D, end: Point2D) -> int:
    for index, point in enumerate(ring):
        following = ring[(index + 1) % len(ring)]
        if _distance(point, start, end) <= ON_FOLD_CM and _distance(following, start, end) <= ON_FOLD_CM:
            return index
    raise ValueError("The fold edge is not on the outline")


def mirrored(points: Sequence[Point2D], start: Point2D, end: Point2D) -> list[Point2D]:
    """Points and their mirror images; a point on the fold line appears once."""
    axis = Vector2D.between(start, end)
    images = [reflect(point, start, axis) for point in points if _distance(point, start, end) > ON_FOLD_CM]
    return [*points, *images]


def unfold_ring(ring: Sequence[Point2D], start: Point2D, end: Point2D) -> list[Point2D]:
    edge = _fold_edge(ring, start, end)
    path = [*ring[edge + 1:], *ring[:edge + 1]]  # from the fold edge's far end round to its near end
    axis = Vector2D.between(start, end)
    return [*path, *(reflect(point, start, axis) for point in reversed(path[1:-1]))]
