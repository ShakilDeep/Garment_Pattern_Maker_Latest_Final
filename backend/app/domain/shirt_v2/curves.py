"""Curve construction for shirt_v2: cubic Béziers whose handles are the 1078375 PDS curve shapes.

A shape is one PDS sew-line curve at size L (``blocks/shirt/shape.py``). shirt_v2 stretches it along x
and y until its ends land on the chart's points: an axis-aligned affine map of the Bézier, so a curve keeps
the PDS angles where they are square (to CF/CB at the neck and hem, level at the underarm) and never gains a
wiggle the PDS curve lacks. An axis the PDS chord barely spans (under 1 cm) scales with the chord length. The body, yoke and sleeve frames (x across, y down) are
the block frame (x along the length, y across) turned a quarter: a block vector (x, y) is (y, -x) here.
"""
from functools import cache
from math import atan2, degrees, hypot, pi, tau

from app.domain.blocks.shirt.draft import positions
from app.domain.blocks.shirt.measures import RECIPES
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.blocks.shirt.shape import chord_handles, shape
from app.domain.tolerances import ANGLE_DEGREES, CURVE_STEPS

Pt = list[float]
Handles = tuple[float, ...]  # PDS chord (x, y), start handle (x, y), end handle (x, y), in cm, this frame
MIN_SPAN = 1.0  # cm


def fractions(piece: str, edge: str) -> Handles:
    """The PDS chord and handles of one block edge, turned into this frame."""
    return _handles()[piece][edge]


@cache
def _handles() -> dict[str, dict[str, Handles]]:
    out: dict[str, dict[str, Handles]] = {}
    for recipe in RECIPES:
        form = shape()[recipe.id]
        at = positions(recipe, reference_measurements(), form)
        for edge, fr in form.handles.items():
            start, end = (at[name] for name in edge.split(":"))
            first, last = chord_handles(start, end, fr)
            chord = (end.y - start.y, start.x - end.x)
            out.setdefault(recipe.id, {})[edge] = (*chord, first.y, -first.x, last.y, -last.x)
    return out


def cubic(start: Pt, end: Pt, handles: Handles, steps: int = CURVE_STEPS) -> list[Pt]:
    """Sample the PDS curve (``fractions``) stretched to run from start to end."""
    cx, cy = end[0] - start[0], end[1] - start[1]
    rx, ry = handles[0], handles[1]
    ratio = hypot(cx, cy) / hypot(rx, ry)
    sx = cx / rx if abs(rx) >= MIN_SPAN else ratio
    sy = cy / ry if abs(ry) >= MIN_SPAN else ratio
    p1 = (start[0] + handles[2] * sx, start[1] + handles[3] * sy)
    p2 = (end[0] + handles[4] * sx, end[1] + handles[5] * sy)
    return bezier(start, p1, p2, end, steps)


def bezier(start: Pt, p1: tuple[float, float], p2: tuple[float, float], end: Pt, steps: int = CURVE_STEPS) -> list[Pt]:
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        w = (u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t)
        out.append([round(w[0] * start[0] + w[1] * p1[0] + w[2] * p2[0] + w[3] * end[0], 6),
                    round(w[0] * start[1] + w[1] * p1[1] + w[2] * p2[1] + w[3] * end[1], 6)])
    return out


def square_end(start: Pt, end: Pt, reach: float = 0.4, steps: int = CURVE_STEPS) -> list[Pt]:
    """A hem curve that leaves ``start`` along its chord and meets ``end`` square to the centre line, as the
    1078375 PDS hems meet CF and CB; the end handle runs back level, ``reach`` of the across distance."""
    cx, cy = end[0] - start[0], end[1] - start[1]
    return bezier(start, (start[0] + reach * cx, start[1] + reach * cy), (end[0] - reach * cx, end[1]), end, steps)


def lerp(start: Pt, end: Pt, t: float) -> Pt:
    """The point at share ``t`` of the straight line from start to end."""
    return [round(start[0] + t * (end[0] - start[0]), 6), round(start[1] + t * (end[1] - start[1]), 6)]


def _turn(a: Pt, b: Pt, c: Pt) -> float:
    delta = atan2(c[1] - b[1], c[0] - b[0]) - atan2(b[1] - a[1], b[0] - a[0])
    return abs(degrees((delta + pi) % tau - pi))


def simplify(points: list[Pt], keep: tuple[tuple[float, float], ...] = ()) -> list[Pt]:
    """Drop the sampled vertices an outline does not need: any that turns the line by no more than the
    outline-quality angle, so straight runs keep only their ends and flat curves lose no visible shape.
    The outline is a ring (a repeated closing point is dropped); points in ``keep`` (notches) always stay."""
    out = [list(p) for p in (points[:-1] if points[0] == points[-1] else points)]
    while len(out) > 3:
        turns = [(_turn(out[i - 1], out[i], out[(i + 1) % len(out)]), i) for i in range(len(out))
                 if tuple(out[i]) not in keep]
        turn, index = min(turns, default=(180.0, 0))
        if turn > ANGLE_DEGREES * 1.5:
            break
        del out[index]
    return out
