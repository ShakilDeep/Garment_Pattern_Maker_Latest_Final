"""Name a PDS piece's sew-line vertices after a recipe's points and cut the sew line into the recipe's edges.

The sew ring is taken counter-clockwise (the PDS draws it clockwise), so an edge "a:b" is the run from a's
vertex forward to b's. A point that is no PDS vertex (the sleeve crown sits at a notch) is the foot of that
notch on the sew line, inserted into the ring as a vertex.
"""
from itertools import pairwise
from math import hypot

from app.domain.interchange import Point
from app.domain.reference import ReferencePiece

SNAP_CM = 0.05  # a locator names the PDS vertex within this distance


def ccw_ring(piece: ReferencePiece) -> list[Point]:
    """The first sew ring, open and counter-clockwise; repeated vertices (the PDS has some) are dropped."""
    raw = piece.outline.sew[0]
    ring = [point for index, point in enumerate(raw) if index == 0 or point != raw[index - 1]]
    if ring[0] == ring[-1]:
        ring.pop()
    twice_area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    return ring if twice_area > 0 else ring[::-1]


def foot(ring: list[Point], at: Point) -> tuple[int, Point]:
    """(index of the ring segment nearest ``at``, the foot of ``at`` on it)."""
    best: tuple[float, int, Point] | None = None
    for index, ((ax, ay), (bx, by)) in enumerate(pairwise(ring + ring[:1])):
        span = (bx - ax) ** 2 + (by - ay) ** 2
        t = min(1.0, max(0.0, ((at[0] - ax) * (bx - ax) + (at[1] - ay) * (by - ay)) / span))
        point = (ax + t * (bx - ax), ay + t * (by - ay))
        distance = hypot(point[0] - at[0], point[1] - at[1])
        if best is None or distance < best[0]:
            best = (distance, index, point)
    if best is None:
        raise ValueError("A PDS sew line needs at least two points")
    return best[1], best[2]


def with_foot(ring: list[Point], at: Point) -> list[Point]:
    index, point = foot(ring, at)
    return ring if point in ring else [*ring[:index + 1], point, *ring[index + 1:]]


def snap(ring: list[Point], name: str, locator: Point) -> int:
    index = min(range(len(ring)), key=lambda i: hypot(ring[i][0] - locator[0], ring[i][1] - locator[1]))
    if hypot(ring[index][0] - locator[0], ring[index][1] - locator[1]) > SNAP_CM:
        raise ValueError(f"No PDS sew-line vertex for {name} near {locator}")
    return index


def travel(ring: list[Point], index: int) -> Point:
    """The sew line's direction of travel through vertex ``index`` (unit; from the samples either side)."""
    (ax, ay), (bx, by) = ring[index - 1], ring[(index + 1) % len(ring)]
    length = hypot(bx - ax, by - ay)
    return (bx - ax) / length, (by - ay) / length


def run(ring: list[Point], start: int, end: int) -> list[Point]:
    """The sew line from vertex ``start`` forward (counter-clockwise) to vertex ``end``."""
    return ring[start:end + 1] if start < end else ring[start:] + ring[:end + 1]
