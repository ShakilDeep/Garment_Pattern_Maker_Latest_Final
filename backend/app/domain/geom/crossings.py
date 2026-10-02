"""Whether an open polyline crosses or touches itself (segments that are not neighbours meeting)."""

from itertools import combinations, pairwise

from app.domain.geom.lines import cross
from app.domain.geom.primitives import Point2D, Vector2D


def _side(a: Point2D, b: Point2D, c: Point2D) -> float:
    return cross(Vector2D.between(a, b), Vector2D.between(a, c))


def _within(a: Point2D, b: Point2D, c: Point2D) -> bool:
    return min(a.x, b.x) <= c.x <= max(a.x, b.x) and min(a.y, b.y) <= c.y <= max(a.y, b.y)


def segments_meet(first: tuple[Point2D, Point2D], second: tuple[Point2D, Point2D]) -> bool:
    (a, b), (c, d) = first, second
    sides = (_side(a, b, c), _side(a, b, d), _side(c, d, a), _side(c, d, b))
    if sides[0] * sides[1] < 0 and sides[2] * sides[3] < 0:
        return True
    touching = ((sides[0], a, b, c), (sides[1], a, b, d), (sides[2], c, d, a), (sides[3], c, d, b))
    return any(side == 0 and _within(p, q, r) for side, p, q, r in touching)


def crosses_itself(points: tuple[Point2D, ...]) -> bool:
    segments = list(pairwise(points))
    return any(
        segments_meet(segments[i], segments[j]) for i, j in combinations(range(len(segments)), 2) if j > i + 1
    )
