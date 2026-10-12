"""Edge report helpers for the PDS surveys (T129, T133a): runs between AAMA turn points, lines and cubics.

A run that one cubic cannot follow within TOLERANCE_CM is also fitted as two cubics, split where a notch
meets it (else at its middle sample).
"""
from itertools import pairwise
from math import hypot

from app.domain.geom.bezier_fit import fit_cubic
from app.domain.geom.primitives import Point2D
from app.infrastructure.aama.corners import split_vertices

TOLERANCE_CM = 0.05  # split report trigger only; the agreed fit tolerance is 0.1 (shirt.md Q4)
STRAIGHT_CM = 0.005  # a run whose samples all lie this close to its chord is a straight line
Point = tuple[float, float]


def fmt(point: Point) -> str:
    return f"({point[0]:.2f}, {point[1]:.2f})"


def runs(ring: tuple[Point, ...]) -> list[list[Point]]:
    """The closed sew ring cut at its turn points into runs from corner to corner."""
    points = list(ring[:-1] if ring[0] == ring[-1] else ring)
    turns, _ = split_vertices(tuple(points))
    starts = sorted({points.index(turn) for turn in turns})
    return [points[a:b + 1] if a < b else points[a:] + points[:b + 1] for a, b in zip(starts, starts[1:] + starts[:1])]


def _off_chord(run: list[Point]) -> float:
    (ax, ay), (bx, by) = run[0], run[-1]
    if (chord := hypot(bx - ax, by - ay)) == 0:
        return 0.0
    return max(abs((bx - ax) * (ay - y) - (ax - x) * (by - ay)) / chord for x, y in run)


def _cubic(run: list[Point]) -> str:
    fit = fit_cubic([Point2D(*point) for point in run])
    s, e = fit.start_handle, fit.end_handle
    return f"handles ({s.x:+.3f}, {s.y:+.3f}) / ({e.x:+.3f}, {e.y:+.3f}), max dev {fit.max_deviation:.3f}"


def _split(run: list[Point], notches: list[Point]) -> tuple[list[Point], list[Point]]:
    """Split at the foot of the nearest notch within 0.05 cm of the run, else at the middle sample."""
    feet = []
    for index, ((ax, ay), (bx, by)) in enumerate(pairwise(run)):
        for nx, ny in notches:
            t = max(0.0, min(1.0, ((nx - ax) * (bx - ax) + (ny - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
            foot = (ax + t * (bx - ax), ay + t * (by - ay))
            feet.append((hypot(foot[0] - nx, foot[1] - ny), index, foot))
    gap, index, foot = min(feet, default=(1.0, 0, run[0]))
    if gap > TOLERANCE_CM:
        middle = len(run) // 2
        return run[:middle + 1], run[middle:]
    return [*run[:index + 1], foot], [foot, *run[index + 1:]]


def edge(run: list[Point], notches: list[Point]) -> str:
    length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(run))
    chord = hypot(run[-1][0] - run[0][0], run[-1][1] - run[0][1])
    head = f"  {fmt(run[0])} -> {fmt(run[-1])}  length {length:.3f}  chord {chord:.3f}  samples {len(run)}"
    if len(run) == 2 or _off_chord(run) <= STRAIGHT_CM:
        return f"{head}  LINE"
    single = fit_cubic([Point2D(*point) for point in run])
    lines = [f"{head}  CUBIC {_cubic(run)}"]
    if single.max_deviation > TOLERANCE_CM and len(run) > 4:
        first, second = _split(run, notches)
        lines.append(f"    split at {fmt(second[0])}: {_cubic(first)}  then {_cubic(second)}")
    return "\n".join(lines)
