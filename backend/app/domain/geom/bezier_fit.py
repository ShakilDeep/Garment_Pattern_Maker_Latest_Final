"""Fit one cubic Bézier to a sampled run with its end points fixed, to read curve shapes off Optitex outlines.

Schneider's least-squares start (Graphics Gems), then Levenberg-Marquardt over the control points and every
sample's parameter together (parameters eliminated per sample, Schur complement; damped, since sliding a
handle along its tangent is almost undone by reparameterizing). A looping fit (a backwards handle) falls back
to the tangent-constrained fit, which is also used when the caller fixes the end directions (``ends``).
"""
from collections.abc import Sequence
from dataclasses import dataclass
from math import hypot

from app.domain.geom.bezier_basis import Control, evaluate, solve, weights
from app.domain.geom.bezier_seed import chord_params, schneider_start, tangent_fit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.tolerances import COORDINATE

ITERATIONS, DAMPING = 400, 1e-3  # rounds; starting Levenberg-Marquardt damping, relative to the squared chord
GROW, SHRINK, GIVE_UP = 4.0, 0.3, 1e12
Step = tuple[list[float], list[float]]


@dataclass(frozen=True)
class CubicFit:
    start_handle: Vector2D
    end_handle: Vector2D
    max_deviation: float


def _gaps(ctrl: Control, points: Sequence[Point2D], params: list[float]) -> list[float]:
    """Each sample's distance to the curve at its parameter."""
    return [hypot(at.x - q.x, at.y - q.y) for q, at in ((q, evaluate(ctrl, t)) for q, t in zip(points, params))]


def _cost(ctrl: Control, points: Sequence[Point2D], params: list[float]) -> float:
    return sum(gap * gap for gap in _gaps(ctrl, points, params))


def _step(ctrl: Control, points: Sequence[Point2D], params: list[float], damping: float) -> Step | None:
    """LM step (control point step P1x P1y P2x P2y, parameter step per sample); the damping augments both the
    control block's diagonal and each parameter's own term before that term is eliminated."""
    matrix, rhs, terms = [[0.0] * 4 for _ in range(4)], [0.0] * 4, []
    for q, t in zip(points, params):
        _, b1, b2, _ = weights(t)
        slope, at = evaluate(ctrl, t, 1), evaluate(ctrl, t)
        gap = (at.x - q.x, at.y - q.y)
        jac = ((b1, 0.0, b2, 0.0), (0.0, b1, 0.0, b2))
        couple = [jac[0][k] * slope.x + jac[1][k] * slope.y for k in range(4)]
        flat, along = slope.x * slope.x + slope.y * slope.y, slope.x * gap[0] + slope.y * gap[1]
        keep = 1.0 / (flat + damping)
        terms.append((couple, along, keep))
        for i in range(4):
            rhs[i] -= jac[0][i] * gap[0] + jac[1][i] * gap[1] - couple[i] * along * keep
            for j in range(4):
                matrix[i][j] += jac[0][i] * jac[0][j] + jac[1][i] * jac[1][j] - couple[i] * couple[j] * keep
    for i in range(4):
        matrix[i][i] += damping
    moved = solve(matrix, rhs)
    if moved is None:
        return None
    return moved, [-(along + sum(c * m for c, m in zip(couple, moved))) * keep for couple, along, keep in terms]


def _moved(ctrl: Control, params: list[float], step: Step) -> tuple[Control, list[float]]:
    delta, shift = step
    inner = (min(max(t + dt, 0.0), 1.0) for t, dt in zip(params[1:-1], shift[1:-1]))
    return ((ctrl[0], Point2D(ctrl[1].x + delta[0], ctrl[1].y + delta[1]),
             Point2D(ctrl[2].x + delta[2], ctrl[2].y + delta[3]), ctrl[3]), [0.0, *inner, 1.0])


def _inward(ctrl: Control) -> bool:
    """Both handles point into the chord; a backwards handle makes the curve loop or cusp."""
    chord = Vector2D.between(ctrl[0], ctrl[3])
    start, end = Vector2D.between(ctrl[0], ctrl[1]), Vector2D.between(ctrl[3], ctrl[2])
    return start.x * chord.x + start.y * chord.y > 0 and end.x * chord.x + end.y * chord.y < 0


def _free_fit(points: Sequence[Point2D]) -> tuple[Control, list[float]]:
    params = chord_params(points)
    ctrl = schneider_start(points, params)
    cost = _cost(ctrl, points, params)
    damping = DAMPING * ((points[-1].x - points[0].x) ** 2 + (points[-1].y - points[0].y) ** 2)
    for _ in range(ITERATIONS if len(points) > 2 else 0):
        step = _step(ctrl, points, params, damping)
        if step is None or damping > GIVE_UP:
            break
        trial, moved = _moved(ctrl, params, step)
        if (trial_cost := _cost(trial, points, moved)) < cost:
            ctrl, params, cost, damping = trial, moved, trial_cost, damping * SHRINK
        else:
            damping *= GROW
    return (ctrl, params) if _inward(ctrl) else tangent_fit(points)


def fit_cubic(points: Sequence[Point2D], ends: tuple[Vector2D, Vector2D] | None = None) -> CubicFit:
    """Best cubic through ``points``; ``ends`` fixes the handle directions (start, and back from the end)."""
    if len(points) < 2 or hypot(points[-1].x - points[0].x, points[-1].y - points[0].y) <= COORDINATE:
        raise ValueError("A curve fit needs two distinct end points")
    ctrl, params = tangent_fit(points, ends) if ends is not None else _free_fit(points)
    deviation = max(_gaps(ctrl, points, params))
    return CubicFit(Vector2D.between(ctrl[0], ctrl[1]), Vector2D.between(ctrl[3], ctrl[2]), deviation)
