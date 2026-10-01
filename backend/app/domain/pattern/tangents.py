"""True unit tangents at the two ends of an outline segment, so corners join curves at their real angle."""

from math import cos, sin

from app.domain.geom.curves import Arc as GeomArc
from app.domain.geom.curves import CubicBezier as GeomCubic
from app.domain.geom.lines import unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.resolve import GeomCurve
from app.domain.tolerances import COORDINATE


def _first_real(*vectors: Vector2D) -> Vector2D:
    """The first vector longer than the coordinate tolerance (a zero Bézier handle falls back)."""
    return unit(next(v for v in vectors if v.length > COORDINATE))


def _cubic(curve: GeomCubic) -> tuple[Vector2D, Vector2D]:
    a, b, c, d = curve.start, curve.control1, curve.control2, curve.end
    start = _first_real(Vector2D.between(a, b), Vector2D.between(a, c), Vector2D.between(a, d))
    end = _first_real(Vector2D.between(c, d), Vector2D.between(b, d), Vector2D.between(a, d))
    return start, end


def _arc(curve: GeomArc) -> tuple[Vector2D, Vector2D]:
    turn = 1 if curve.end_angle > curve.start_angle else -1
    return tuple(  # type: ignore[return-value]
        Vector2D(-sin(angle) * turn, cos(angle) * turn) for angle in (curve.start_angle, curve.end_angle)
    )


def end_tangents(curve: GeomCurve, start: Point2D, end: Point2D) -> tuple[Vector2D, Vector2D]:
    if isinstance(curve, GeomCubic):
        return _cubic(curve)
    if isinstance(curve, GeomArc):
        return _arc(curve)
    chord = unit(Vector2D.between(start, end))
    return chord, chord
