"""Cubic fit helpers: chord-length parameters, Schneider's least-squares start, and his tangent-constrained fit.

The tangent-constrained fit keeps each handle along its end's direction (the run's first and last step), so it
can never point backwards and loop; ``fit_cubic`` falls back to it when the free fit would.
"""
from collections.abc import Sequence
from itertools import pairwise
from math import hypot

from app.domain.geom.bezier_basis import Control, evaluate, solve, weights
from app.domain.geom.lines import unit
from app.domain.geom.primitives import Point2D, Vector2D

TANGENT_ROUNDS = 60  # fixed budget of reparameterize-and-solve rounds for the (fallback) tangent fit
FLAT = 1e-18


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


def _dot(u: Vector2D, v: Vector2D) -> float:
    return u.x * v.x + u.y * v.y


def _along(point: Point2D, direction: Vector2D, distance: float) -> Point2D:
    return Point2D(point.x + direction.x * distance, point.y + direction.y * distance)


def _tangent_lengths(points: Sequence[Point2D], params: list[float], ends: tuple[Vector2D, Vector2D]) -> Control:
    a, d = points[0], points[-1]
    rows = []
    for q, t in zip(points, params):
        w = weights(t)
        near, far = w[0] + w[1], w[2] + w[3]
        rest = Vector2D(q.x - near * a.x - far * d.x, q.y - near * a.y - far * d.y)
        rows.append((Vector2D(w[1] * ends[0].x, w[1] * ends[0].y), Vector2D(w[2] * ends[1].x, w[2] * ends[1].y), rest))
    gram = [[sum(_dot(r[i], r[j]) for r in rows) for j in (0, 1)] for i in (0, 1)]
    lengths = solve(gram, [sum(_dot(r[i], r[2]) for r in rows) for i in (0, 1)])
    third = hypot(d.x - a.x, d.y - a.y) / 3
    first, second = lengths if lengths and min(lengths) > 0 else (third, third)
    return a, _along(a, ends[0], first), _along(d, ends[1], second), d


def _closest(ctrl: Control, q: Point2D, t: float) -> float:
    at, slope, bend = evaluate(ctrl, t), evaluate(ctrl, t, 1), evaluate(ctrl, t, 2)
    gap = Vector2D(at.x - q.x, at.y - q.y)
    curvature = slope.x * slope.x + slope.y * slope.y + gap.x * bend.x + gap.y * bend.y
    if abs(curvature) <= FLAT:
        return t
    return min(max(t - (gap.x * slope.x + gap.y * slope.y) / curvature, 0.0), 1.0)


def tangent_fit(points: Sequence[Point2D], ends: tuple[Vector2D, Vector2D] | None = None
                ) -> tuple[Control, list[float]]:
    """Handles along the given end directions (by default the run's first and last steps), lengths by least
    squares, parameters refined by Newton steps."""
    a, d = points[0], points[-1]
    ends = ends or (unit(Vector2D.between(a, next(p for p in points[1:] if p != a))),
                    unit(Vector2D.between(d, next(p for p in reversed(points[:-1]) if p != d))))
    params = chord_params(points)
    ctrl = _tangent_lengths(points, params, ends)
    for _ in range(TANGENT_ROUNDS):
        params = [0.0, *(_closest(ctrl, q, t) for q, t in zip(points[1:-1], params[1:-1])), 1.0]
        ctrl = _tangent_lengths(points, params, ends)
    return ctrl, params
