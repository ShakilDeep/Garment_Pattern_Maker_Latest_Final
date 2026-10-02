"""Parameter readers for the draft tools: each refuses a bad value with a ValueError (400) naming it."""

from app.application.cad.command import Params
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.point import finite_point, is_real

PAIR = 2


def xy(params: Params, name: str) -> Point2D:
    value = params[name]
    if not isinstance(value, (list, tuple)) or len(value) != PAIR:
        raise ValueError(f"{name} must be an [x, y] pair of numbers")
    return finite_point(*value)


def offset(params: Params, name: str) -> Vector2D:
    point = xy(params, name)
    return Vector2D(point.x, point.y)


def number(params: Params, name: str) -> float:
    value = params[name]
    if not is_real(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)  # type: ignore[arg-type]


def positive(params: Params, name: str) -> float:
    value = number(params, name)
    if value <= 0:
        raise ValueError(f"{name} must be a positive number of cm")
    return value


def count(params: Params, name: str) -> int:
    value = params[name]
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a whole number of at least 1")
    return value


def text(params: Params, name: str) -> str:
    value = params[name]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value
