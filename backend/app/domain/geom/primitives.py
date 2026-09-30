"""Point, vector and open-path primitives with the shared coordinate epsilon."""
from dataclasses import dataclass
from math import hypot

from app.domain.tolerances import COORDINATE, SVG_DECIMALS

EPSILON = COORDINATE


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def to_data(self):
        return [round(self.x, SVG_DECIMALS), round(self.y, SVG_DECIMALS)]


@dataclass(frozen=True)
class Vector2D:
    x: float
    y: float

    @classmethod
    def between(cls, start, end):
        return cls(end.x - start.x, end.y - start.y)

    @property
    def length(self):
        return hypot(self.x, self.y)


@dataclass(frozen=True)
class LineSegment:
    start: Point2D
    end: Point2D

    @property
    def length(self):
        return Vector2D.between(self.start, self.end).length


@dataclass(frozen=True)
class Polyline:
    points: tuple[Point2D, ...]

    def __post_init__(self):
        if len(self.points) < 2:
            raise ValueError("A polyline requires at least two points")

    def to_data(self):
        return [point.to_data() for point in self.points]
