"""Closed outlines and their axis-aligned bounds."""
from dataclasses import dataclass

from app.domain.geom.primitives import Point2D


@dataclass(frozen=True)
class ClosedPath:
    points: tuple[Point2D, ...]

    def __post_init__(self):
        if len(self.points) < 3:
            raise ValueError("A closed path requires at least three points")
        if self.points[-1] != self.points[0]:
            object.__setattr__(self, "points", (*self.points, self.points[0]))

    def to_data(self):
        return [point.to_data() for point in self.points]

    @property
    def bounds(self):
        return BoundingBox.from_points(self.points)


@dataclass(frozen=True)
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def from_points(cls, points):
        values = tuple(points)
        if not values:
            raise ValueError("A bounding box requires points")
        return cls(min(p.x for p in values), min(p.y for p in values),
                   max(p.x for p in values), max(p.y for p in values))

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def height(self):
        return self.max_y - self.min_y
