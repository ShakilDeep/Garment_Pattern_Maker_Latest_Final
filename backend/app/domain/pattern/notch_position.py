"""Where curve parameter t lies on an outline segment: a fraction on lines and arcs, Bernstein on cubics."""

from math import cos, sin

from app.domain.geom.curves import Arc as GeomArc
from app.domain.geom.curves import CubicBezier as GeomCubic
from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import Notch
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import GeomCurve, resolve_segment


def point_on(curve: GeomCurve, t: float) -> Point2D:
    if isinstance(curve, GeomCubic):
        a, b, c, d = curve.start, curve.control1, curve.control2, curve.end
        u = 1 - t
        weights = (u**3, 3 * u * u * t, 3 * u * t * t, t**3)
        return Point2D(sum(w * p.x for w, p in zip(weights, (a, b, c, d))),
                       sum(w * p.y for w, p in zip(weights, (a, b, c, d))))
    if isinstance(curve, GeomArc):
        angle = curve.start_angle + (curve.end_angle - curve.start_angle) * t
        return Point2D(curve.center.x + curve.radius * cos(angle), curve.center.y + curve.radius * sin(angle))
    start, end = curve.start, curve.end
    return Point2D(start.x + t * (end.x - start.x), start.y + t * (end.y - start.y))


def notch_position(piece: Piece, notch: Notch) -> Point2D:
    positions = {p.id: p.position for p in piece.points}
    segment = next(s for s in piece.outline if s.id == notch.segment)
    return point_on(resolve_segment(segment, positions), notch.t)
