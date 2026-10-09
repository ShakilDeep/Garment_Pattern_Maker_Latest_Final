"""Split a closed cut ring's vertices into AAMA turn points (corners) and curve points.

Pure geometry: a vertex is a turn point when the outline changes direction there by at least
``CORNER_TURN_DEG``; every other vertex lies on a curve. Nothing about construction is assumed.
"""
from math import atan2, degrees

from app.domain.interchange import Point, Ring

CORNER_TURN_DEG = 30.0


def _turn_deg(previous: Point, vertex: Point, following: Point) -> float:
    incoming = atan2(vertex[1] - previous[1], vertex[0] - previous[0])
    outgoing = atan2(following[1] - vertex[1], following[0] - vertex[0])
    turn = abs(degrees(outgoing - incoming)) % 360.0  # both atan2 angles are radians; convert the difference
    return min(turn, 360.0 - turn)


def split_vertices(ring: Ring) -> tuple[list[Point], list[Point]]:
    """(turn points, curve points) in ring order; the ring is closed implicitly."""
    turns: list[Point] = []
    curves: list[Point] = []
    count = len(ring)
    for index, vertex in enumerate(ring):
        turn = _turn_deg(ring[index - 1], vertex, ring[(index + 1) % count])
        (turns if turn >= CORNER_TURN_DEG else curves).append(vertex)
    return turns, curves
