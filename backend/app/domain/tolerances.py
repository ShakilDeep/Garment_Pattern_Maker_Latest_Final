"""Central numeric policy for deterministic demo geometry."""

from math import isfinite, ulp

COORDINATE = 1e-6
LENGTH_CM = 0.01
ANGLE_DEGREES = 0.1
CURVE_STEPS = 24
INTERSECTION = 1e-6
SVG_DECIMALS = 6
# Pattern-model precision (1e-6 cm); changing it changes every stored geometry hash.
MODEL_DECIMALS = 6
# Notch curve parameter t: a 1e-9 step moves a notch < 1e-6 cm along any edge up to 1000 cm long.
NOTCH_T_DECIMALS = 9
SLEEVE_EASE_CM = 2.0
SOURCE_DIMENSION_CM = 1.0


def within_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    """Inclusive threshold with two ULPs for representation/subtraction rounding."""
    if not all(isfinite(v) for v in (actual, expected, tolerance)) or tolerance < 0:
        return False
    roundoff = 2 * max(ulp(actual), ulp(expected), ulp(tolerance))
    return abs(actual - expected) <= tolerance + roundoff
