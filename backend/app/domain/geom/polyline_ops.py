"""Measurements and curve sampling over raw [x, y] point lists used by drafting."""
from itertools import pairwise
from math import hypot

from app.domain.tolerances import CURVE_STEPS


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
