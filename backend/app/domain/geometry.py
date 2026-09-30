from dataclasses import dataclass
from itertools import pairwise
from math import cos, hypot, isfinite, sin

from app.domain.tolerances import COORDINATE, CURVE_STEPS, SVG_DECIMALS

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


@dataclass(frozen=True)
class Transform2D:
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def apply(self, point):
        return Point2D(self.a*point.x + self.c*point.y + self.e,
                       self.b*point.x + self.d*point.y + self.f)

    @classmethod
    def translation(cls, x, y):
        return cls(e=x, f=y)

    @classmethod
    def rotation(cls, angle):
        return cls(a=cos(angle), b=sin(angle), c=-sin(angle), d=cos(angle))



def quadratic(a, b, c):
    return [
        [
            round((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * b[0] + t * t * c[0], 6),
            round((1 - t) ** 2 * a[1] + 2 * (1 - t) * t * b[1] + t * t * c[1], 6),
        ]
        for t in (i / CURVE_STEPS for i in range(CURVE_STEPS + 1))
    ]


def length(points):
    return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(points))


def area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in pairwise(points))) / 2


def make_piece(name, points, quantity=2, fold=False, seams=None):
    if points[-1] != points[0]:
        points = [*points, points[0]]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    points = [[round(x - x0, 6), round(y - y0, 6)] for x, y in points]
    width, height = max(p[0] for p in points), max(p[1] for p in points)
    if not all(isfinite(c) for p in points for c in p) or area(points) <= EPSILON:
        raise ValueError(f"{name}: invalid geometry")
    return {
        "id": name.lower().replace(" ", "_"),
        "name": name,
        "points": points,
        "quantity": quantity,
        "cut_on_fold": fold,
        "width": width,
        "height": height,
        "area": area(points),
        "perimeter": length(points),
        "grainline": [[width / 2, height * 0.35], [width / 2, height * 0.65]],
        "notches": [points[len(points) // 3]],
        "seams": seams or {},
    }


def unfold(half):
    return [*half, *[[-x, y] for x, y in reversed(half)][1:]]
