"""Resolve a raw, possibly self-crossing offset ring to the cut outline: its non-zero-winding envelope.

The ring is noded at every crossing and polygonized. A face is kept when the raw ring winds around it at
least once in the ring's own direction (the "positive" fill rule of polygon offsetting, as in Clipper), so
swallowtails and reversed lobes drop out and doubly-covered curls merge in. Corner shapes are kept exactly;
holes in the result are filled (the cut follows the outer edge).
"""

import shapely
from shapely.geometry import LineString, Polygon

from app.domain.geom.primitives import Point2D


def winding(ring: tuple[Point2D, ...], x: float, y: float) -> int:
    """How many times the closed ring winds counter-clockwise around (x, y)."""
    total = 0
    for a, b in zip(ring, (*ring[1:], ring[0])):
        side = (b.x - a.x) * (y - a.y) - (x - a.x) * (b.y - a.y)
        if a.y <= y < b.y and side > 0:
            total += 1
        elif b.y <= y < a.y and side < 0:
            total -= 1
    return total


def envelope(ring: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
    """The cut outline as an open ring wound like the input; ValueError when it falls apart in pieces."""
    side = 1 if sum(a.x * b.y - b.x * a.y for a, b in zip(ring, (*ring[1:], ring[0]))) > 0 else -1
    closed = LineString([(p.x, p.y) for p in (*ring, ring[0])])
    faces = shapely.get_parts(shapely.polygonize(shapely.get_parts(shapely.node(closed))))
    kept = [face for face in faces if winding(ring, *face.representative_point().coords[0]) * side > 0]
    union = shapely.union_all(kept)
    if not isinstance(union, Polygon) or union.is_empty:
        raise ValueError("the seam allowance splits the cut outline into separate parts")
    coords = list(union.exterior.coords)[:-1]
    if union.exterior.is_ccw != (side > 0):
        coords.reverse()
    return tuple(Point2D(x, y) for x, y in coords)
