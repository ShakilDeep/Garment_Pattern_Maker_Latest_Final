"""Starting guess for the cubic fit: chord-length parameters and Schneider's least-squares inner points."""
from collections.abc import Sequence
from itertools import pairwise
from math import hypot

from app.domain.geom.bezier_basis import Control, solve, weights
from app.domain.geom.primitives import Point2D


def chord_params(points: Sequence[Point2D]) -> list[float]:
    """Each sample's share of the run's polyline length, 0 at the first sample and 1 at the last."""
    steps = [hypot(b.x - a.x, b.y - a.y) for a, b in pairwise(points)]
    total, run, params = sum(steps), 0.0, [0.0]
    for step in steps:
        run += step
        params.append(min(run / total, 1.0))
    return params


def _thirds(a: Point2D, d: Point2D) -> Control:
    return a, Point2D(a.x + (d.x - a.x) / 3, a.y + (d.y - a.y) / 3), Point2D(d.x + (a.x - d.x) / 3,
                                                                          d.y + (a.y - d.y) / 3), d


def schneider_start(points: Sequence[Point2D], params: list[float]) -> Control:
    """Inner control points minimizing the squared error at fixed parameters (straight thirds if singular)."""
    a, d = points[0], points[-1]
    terms = [(weights(t), q) for q, t in zip(points, params)]
    gram = [[sum(w[i] * w[j] for w, _ in terms) for j in (1, 2)] for i in (1, 2)]
    inner = [
        solve(gram, [sum(w[i] * (getattr(q, axis) - w[0] * getattr(a, axis) - w[3] * getattr(d, axis))
                         for w, q in terms) for i in (1, 2)])
        for axis in "xy"
    ]
    if inner[0] is None or inner[1] is None:
        return _thirds(a, d)
    return a, Point2D(inner[0][0], inner[1][0]), Point2D(inner[0][1], inner[1][1]), d
