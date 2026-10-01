"""Infinite-line helpers for offset construction: intersection and reflection across an axis."""

from app.domain.geom.primitives import Point2D, Vector2D

PARALLEL = 1e-12  # |cross| of unit directions below this means the lines never meet usefully


def cross(first: Vector2D, second: Vector2D) -> float:
    return first.x * second.y - first.y * second.x


def unit(direction: Vector2D) -> Vector2D:
    length = direction.length
    return Vector2D(direction.x / length, direction.y / length)


def along(point: Point2D, direction: Vector2D, distance: float) -> Point2D:
    return Point2D(point.x + direction.x * distance, point.y + direction.y * distance)


def intersect(p: Point2D, d: Vector2D, q: Point2D, e: Vector2D) -> Point2D | None:
    """Where the line through p along d meets the line through q along e; None when (nearly) parallel."""
    denominator = cross(d, e)
    if abs(denominator) <= PARALLEL:
        return None
    t = cross(Vector2D.between(p, q), e) / denominator
    return along(p, d, t)


def reflect(point: Point2D, origin: Point2D, axis: Vector2D) -> Point2D:
    """Mirror a point across the line through origin along axis."""
    direction = unit(axis)
    offset = Vector2D.between(origin, point)
    projection = offset.x * direction.x + offset.y * direction.y
    foot = along(origin, direction, projection)
    return Point2D(2 * foot.x - point.x, 2 * foot.y - point.y)


def reflect_direction(direction: Vector2D, axis: Vector2D) -> Vector2D:
    origin = Point2D(0.0, 0.0)
    image = reflect(Point2D(direction.x, direction.y), origin, axis)
    return Vector2D(image.x, image.y)
