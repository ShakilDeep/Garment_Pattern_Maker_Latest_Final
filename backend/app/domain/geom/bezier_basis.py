"""Cubic Bézier evaluation by Bernstein weights, and a small dense linear solve, for the curve fit."""
from collections.abc import Sequence

from app.domain.geom.primitives import Point2D, Vector2D

Control = tuple[Point2D, Point2D, Point2D, Point2D]
PIVOT = 1e-14


def weights(t: float, order: int = 0) -> tuple[float, float, float, float]:
    """Bernstein weights of the curve (order 0) or of its first or second derivative at t."""
    u = 1 - t
    if order == 0:
        return u**3, 3 * u * u * t, 3 * u * t * t, t**3
    if order == 1:
        return -3 * u * u, 3 * u * u - 6 * u * t, 6 * u * t - 3 * t * t, 3 * t * t
    return 6 * u, 6 * t - 12 * u, 6 * u - 12 * t, 6 * t


def evaluate(ctrl: Control, t: float, order: int = 0) -> Vector2D:
    w = weights(t, order)
    return Vector2D(sum(k * p.x for k, p in zip(w, ctrl)), sum(k * p.y for k, p in zip(w, ctrl)))


def solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float]) -> list[float] | None:
    """Gaussian elimination with partial pivoting; None when the system is singular."""
    size = len(rhs)
    rows = [[*matrix[i], rhs[i]] for i in range(size)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
        if abs(rows[pivot][col]) <= PIVOT:
            return None
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(col + 1, size):
            factor = rows[r][col] / rows[col][col]
            rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col])]
    solution = [0.0] * size
    for r in reversed(range(size)):
        solution[r] = (rows[r][size] - sum(rows[r][c] * solution[c] for c in range(r + 1, size))) / rows[r][r]
    return solution
