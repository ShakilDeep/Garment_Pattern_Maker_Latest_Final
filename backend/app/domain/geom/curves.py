"""Sampled curve primitives: cubic Bézier and circular arc."""
from dataclasses import dataclass
from math import cos, sin

from app.domain.geom.primitives import Point2D
from app.domain.tolerances import CURVE_STEPS


@dataclass(frozen=True)
class CubicBezier:
    start: Point2D
    control1: Point2D
    control2: Point2D
    end: Point2D

    def sample(self, steps=CURVE_STEPS):
        if steps < 1:
            raise ValueError("Curve sampling requires at least one step")
        result = []
        for index in range(steps + 1):
            t = index / steps
            inverse = 1 - t
            x = (inverse**3 * self.start.x + 3 * inverse**2 * t * self.control1.x
                 + 3 * inverse * t**2 * self.control2.x + t**3 * self.end.x)
            y = (inverse**3 * self.start.y + 3 * inverse**2 * t * self.control1.y
                 + 3 * inverse * t**2 * self.control2.y + t**3 * self.end.y)
            result.append(Point2D(x, y))
        return tuple(result)


@dataclass(frozen=True)
class Arc:
    center: Point2D
    radius: float
    start_angle: float
    end_angle: float

    def sample(self, steps=CURVE_STEPS):
        if self.radius <= 0 or steps < 1:
            raise ValueError("An arc requires a positive radius and sampling step count")
        return tuple(Point2D(
            self.center.x + self.radius * cos(self.start_angle + (self.end_angle-self.start_angle)*i/steps),
            self.center.y + self.radius * sin(self.start_angle + (self.end_angle-self.start_angle)*i/steps),
        ) for i in range(steps + 1))
