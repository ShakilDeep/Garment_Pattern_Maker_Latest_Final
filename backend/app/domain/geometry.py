"""Facade over app.domain.geom: the stable import path for geometry primitives and helpers."""
from app.domain.geom.curves import Arc, CubicBezier
from app.domain.geom.paths import BoundingBox, ClosedPath
from app.domain.geom.piece_builder import make_piece, unfold
from app.domain.geom.polyline_ops import area, length, quadratic
from app.domain.geom.primitives import EPSILON, LineSegment, Point2D, Polyline, Vector2D
from app.domain.geom.transform import Transform2D

__all__ = [
    "EPSILON",
    "Arc",
    "BoundingBox",
    "ClosedPath",
    "CubicBezier",
    "LineSegment",
    "Point2D",
    "Polyline",
    "Transform2D",
    "Vector2D",
    "area",
    "length",
    "make_piece",
    "quadratic",
    "unfold",
]
