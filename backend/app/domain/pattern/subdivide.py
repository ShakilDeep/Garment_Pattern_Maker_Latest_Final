"""Exact splitting and re-joining of curves (CAD-02 split/join): de Casteljau for cubics, angles for arcs.

`merged_cubic` only succeeds when the two cubics really are one cubic split in two, so a join never
approximates a shape.
"""

from math import atan, tan

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.tolerances import LENGTH_CM

Quad = tuple[Point2D, Point2D, Point2D, Point2D]


def _mix(a: Point2D, b: Point2D, t: float) -> Point2D:
    return Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


def split_cubic(points: Quad, t: float) -> tuple[Quad, Quad]:
    a, b, c, d = points
    ab, bc, cd = _mix(a, b, t), _mix(b, c, t), _mix(c, d, t)
    abc, bcd = _mix(ab, bc, t), _mix(bc, cd, t)
    middle = _mix(abc, bcd, t)
    return (a, ab, abc, middle), (middle, bcd, cd, d)


def _close(first: Quad, second: Quad) -> bool:
    return all(Vector2D.between(p, q).length <= LENGTH_CM for p, q in zip(first, second))


def merged_cubic(left: Quad, right: Quad) -> tuple[Quad, float] | None:
    """The cubic that `left` and `right` were split from, and the split parameter; None if there is none."""
    before, after = Vector2D.between(left[2], left[3]).length, Vector2D.between(right[0], right[1]).length
    if before + after == 0:
        return None
    u = before / (before + after)
    if not 0 < u < 1:
        return None
    a, d = left[0], right[3]
    b = Point2D(a.x + (left[1].x - a.x) / u, a.y + (left[1].y - a.y) / u)
    c = Point2D(d.x + (right[2].x - d.x) / (1 - u), d.y + (right[2].y - d.y) / (1 - u))
    again_left, again_right = split_cubic((a, b, c, d), u)
    return ((a, b, c, d), u) if _close(again_left, left) and _close(again_right, right) else None


def split_bulge(bulge: float, t: float) -> tuple[float, float]:
    """Bulges of the two arcs a bulge-`bulge` arc splits into at angle fraction t."""
    angle = 4 * atan(bulge)
    return tan(angle * t / 4), tan(angle * (1 - t) / 4)


def merged_bulge(first: float, second: float) -> tuple[float, float]:
    """The bulge of two consecutive arcs of one circle, and the first arc's share of the angle."""
    first_angle, second_angle = 4 * atan(first), 4 * atan(second)
    total = first_angle + second_angle
    return tan(total / 4), first_angle / total
