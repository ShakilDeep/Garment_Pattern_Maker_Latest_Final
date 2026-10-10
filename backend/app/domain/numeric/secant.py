"""Secant root finding in one unknown (T131 seam truing): x with f(x) = 0, started from a guess."""
from collections.abc import Callable

from app.domain.tolerances import COORDINATE

FIRST_STEP = 0.1  # cm: the second probe beside the guess
TOLERANCE = 2 * COORDINATE  # |f| at which the root is taken: geometry is quantized to 1e-6 cm
ROUNDS = 80
MAX_STEP = 2.0  # cm: a shallow equation cannot throw the next trial further than this


def solve_1d(f: Callable[[float], float], guess: float) -> float:
    a, b = guess, guess + FIRST_STEP
    fa, fb = f(a), f(b)
    for _ in range(ROUNDS):
        if abs(fb) <= TOLERANCE:
            return b
        if fb == fa:
            raise ValueError("The truing equation does not change with its measurement")
        step = max(-MAX_STEP, min(MAX_STEP, -fb * (b - a) / (fb - fa)))
        a, b, fa = b, b + step, fb
        fb = f(b)
    raise ValueError("The truing equation did not converge")
