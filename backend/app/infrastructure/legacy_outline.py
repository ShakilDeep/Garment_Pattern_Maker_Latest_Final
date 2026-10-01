"""V5 polyline <-> pattern outline: vertex points, straight segments, anchored notches and derived metrics."""

from math import hypot, isfinite

from app.domain.geom.polyline_ops import area, length
from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import Notch
from app.domain.pattern.codec_values import point_at, xy
from app.domain.pattern.ids import AnnotationId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.tolerances import COORDINATE

MIN_RING_LENGTH = 2


def outline_from_ring(ring: object) -> tuple[tuple[PatternPoint, ...], tuple[Line, ...]]:
    """A closed V5 [x, y] list (last point equal to the first) -> points p0..pn-1 and lines s0..sn-1."""
    if not isinstance(ring, list) or len(ring) < MIN_RING_LENGTH or ring[0] != ring[-1]:
        raise ValueError("V5 points must be a closed [x, y] list whose last point equals the first")
    points = tuple(PatternPoint(PointId(f"p{i}"), point_at(xy)) for i, xy in enumerate(ring[:-1]))
    count = len(points)
    lines = tuple(Line(SegmentId(f"s{i}"), points[i].id, points[(i + 1) % count].id) for i in range(count))
    return points, lines


def _parameter(at: Point2D, start: Point2D, end: Point2D) -> float:
    dx, dy = end.x - start.x, end.y - start.y
    t = ((at.x - start.x) * dx + (at.y - start.y) * dy) / (dx * dx + dy * dy)
    if not isfinite(t):
        raise ValueError("V5 coordinates are too large to place a notch")
    return min(max(t, 0.0), 1.0)


def position_on(start: Point2D, end: Point2D, t: float) -> Point2D:
    if t == 1:
        return end
    return Point2D(start.x + t * (end.x - start.x), start.y + t * (end.y - start.y))


def notch_on_outline(index: int, raw: object, points: tuple[PatternPoint, ...], lines: tuple[Line, ...]) -> Notch:
    """Anchor a V5 [x, y] notch on its nearest segment (first one wins a tie); loose notches are rejected."""
    at = point_at(raw)
    positions = {p.id: p.position for p in points}
    candidates = []
    for line in lines:
        start, end = positions[line.start], positions[line.end]
        t = _parameter(at, start, end)
        foot = position_on(start, end, t)
        candidates.append((hypot(at.x - foot.x, at.y - foot.y), t, line))
    distance, t, line = min(candidates, key=lambda candidate: candidate[0])
    if distance > COORDINATE:
        raise ValueError(f"V5 notch {raw!r} is not on the outline")
    return Notch(AnnotationId(f"n{index}"), line.id, t)


def ring_of(piece: Piece) -> list[list[float]]:
    """The closed V5 point list of a straight-line outline (see legacy_limits), in outline order."""
    positions = {p.id: p.position for p in piece.points}
    ring = [[positions[s.start].x, positions[s.start].y] for s in piece.outline]
    return [*ring, ring[0]]


def notch_positions(piece: Piece) -> list[list[float]]:
    positions = {p.id: p.position for p in piece.points}
    segments = {s.id: s for s in piece.outline}
    placed = []
    for notch in piece.notches:
        segment = segments[notch.segment]
        at = position_on(positions[segment.start], positions[segment.end], notch.t)
        placed.append(xy(at))
    return placed


def derived_metrics(ring: list[list[float]]) -> dict:
    """V5 size fields, computed as V5 `make_piece` computes them."""
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return {"width": max(xs) - min(xs), "height": max(ys) - min(ys), "area": area(ring), "perimeter": length(ring)}
