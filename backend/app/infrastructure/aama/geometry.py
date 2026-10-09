"""Shapely measurements of interchange pieces: a piece cut on the fold is its half plus the mirrored half."""
from shapely import union_all
from shapely.geometry import LinearRing, Polygon
from shapely.geometry import Point as ShapelyPoint

from app.domain.interchange import InterchangePiece, Point, Ring, Segment

CM2_PER_M2 = 10_000.0


def reflect(point: Point, axis: Segment) -> Point:
    """Mirror ``point`` across the infinite line through ``axis``."""
    (x1, y1), (x2, y2) = axis
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    if length2 == 0:
        raise ValueError("A mirror line needs two distinct points")
    t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / length2
    foot = (x1 + t * dx, y1 + t * dy)
    return 2 * foot[0] - point[0], 2 * foot[1] - point[1]


def whole_outline(piece: InterchangePiece):
    half = Polygon(piece.cut)
    if piece.mirror is None:
        return half
    return union_all([half, Polygon([reflect(p, piece.mirror) for p in piece.cut])])


def piece_area_m2(piece: InterchangePiece) -> float:
    return whole_outline(piece).area / CM2_PER_M2


def distance_to_ring(point: Point, ring: Ring) -> float:
    return LinearRing(ring).distance(ShapelyPoint(point))
