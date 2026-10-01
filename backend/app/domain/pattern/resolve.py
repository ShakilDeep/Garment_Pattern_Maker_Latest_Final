"""Resolve a piece's id-referenced outline into the sampled domain/geom primitives (absolute positions)."""

from math import atan, atan2

from app.domain.geom.curves import Arc as GeomArc
from app.domain.geom.curves import CubicBezier as GeomCubic
from app.domain.geom.primitives import LineSegment, Point2D, Vector2D
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Arc, CubicBezier, Segment

GeomCurve = LineSegment | GeomCubic | GeomArc


def arc_from_bulge(start: Point2D, end: Point2D, bulge: float) -> GeomArc:
    """DXF bulge b = tan(theta/4).

    The centre sits on the chord's left normal, chord * (1 - b^2) / (4b) from its middle.
    """
    chord = Vector2D.between(start, end)
    length = chord.length
    offset = length * (1 - bulge * bulge) / (4 * bulge)
    centre = Point2D(
        (start.x + end.x) / 2 - chord.y / length * offset, (start.y + end.y) / 2 + chord.x / length * offset
    )
    begin = atan2(start.y - centre.y, start.x - centre.x)
    radius = length * (1 + bulge * bulge) / (4 * abs(bulge))
    return GeomArc(centre, radius, begin, begin + 4 * atan(bulge))


def resolve_segment(segment: Segment, positions: dict[PointId, Point2D]) -> GeomCurve:
    start, end = positions[segment.start], positions[segment.end]
    if isinstance(segment, CubicBezier):
        first = Point2D(start.x + segment.start_handle.x, start.y + segment.start_handle.y)
        second = Point2D(end.x + segment.end_handle.x, end.y + segment.end_handle.y)
        return GeomCubic(start, first, second, end)
    if isinstance(segment, Arc):
        return arc_from_bulge(start, end, segment.bulge)
    return LineSegment(start, end)


def outline_curves(piece: Piece) -> tuple[GeomCurve, ...]:
    positions = {p.id: p.position for p in piece.points}
    return tuple(resolve_segment(segment, positions) for segment in piece.outline)
