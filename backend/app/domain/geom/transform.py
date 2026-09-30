"""Affine 2D transform used for display and placement without mutating geometry."""
from dataclasses import dataclass
from math import cos, sin

from app.domain.geom.primitives import Point2D


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
