"""Construction geometry for the draft tools (CAD-01): offsets, parallels, perpendicular feet, intersections.

Pure functions in cm. "Outside" follows the outline's own winding, as the seam allowance does (PM-03).
"""

from itertools import pairwise
from math import radians, sin

from app.domain.geom.crossings import crosses_itself
from app.domain.geom.lines import along, cross, intersect, unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.edges import edge_polyline, orientation, stitch_ring
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Line
from app.domain.tolerances import ANGLE_DEGREES, COORDINATE

STRAIGHT_LINE_POINTS = 2


def _outward(direction: Vector2D, side: int) -> Vector2D:
    return Vector2D(direction.y * side, -direction.x * side)


def offset_edge(piece: Piece, segment_id: SegmentId, distance: float) -> tuple[Point2D, ...]:
    """The edge's polyline moved `distance` cm outside the piece (negative: inside), mitred at its bends."""
    segment = next((s for s in piece.outline if s.id == segment_id), None)
    if segment is None:
        raise KeyError(f"Unknown edge {segment_id}")
    if abs(distance) <= COORDINATE:
        raise ValueError("distance must be a non-zero number of cm")
    points = edge_polyline(segment, {p.id: p.position for p in piece.points})
    side = orientation(stitch_ring(piece))
    normals = [_outward(unit(Vector2D.between(a, b)), side) for a, b in pairwise(points)]
    shifted = [along(points[0], normals[0], distance)]
    for point, before, after in zip(points[1:-1], normals, normals[1:]):
        mitre = Vector2D(before.x + after.x, before.y + after.y)
        if mitre.length <= COORDINATE:
            raise ValueError(f"Edge {segment_id} doubles back on itself and cannot be offset")
        direction = unit(mitre)
        shifted.append(along(point, direction, distance / (direction.x * before.x + direction.y * before.y)))
    result = (*shifted, along(points[-1], normals[-1], distance))
    if crosses_itself(result) or _reverses(points, result):
        raise ValueError(f"Offsetting edge {segment_id} by {distance} cm folds the line over itself")
    return result


def _reverses(original: tuple[Point2D, ...], shifted: tuple[Point2D, ...]) -> bool:
    """An offset deeper than the curve's radius turns its pieces backwards (the line folds over)."""
    pairs = zip(pairwise(original), pairwise(shifted))
    return any(
        (b.x - a.x) * (d.x - c.x) + (b.y - a.y) * (d.y - c.y) <= 0 for (a, b), (c, d) in pairs
    )


def straight_ends(piece: Piece, reference: str) -> tuple[Point2D, Point2D]:
    """A straight outline edge or a two-point internal line of the piece, by id, as its two end points."""
    positions = {p.id: p.position for p in piece.points}
    for segment in piece.outline:
        if str(segment.id) == reference:
            if not isinstance(segment, Line):
                raise ValueError(f"Edge {reference} is curved; this tool needs a straight edge or line")
            return positions[segment.start], positions[segment.end]
    for line in piece.internal_lines:
        if str(line.id) == reference:
            if len(line.points) != STRAIGHT_LINE_POINTS:
                raise ValueError(f"Line {reference} bends; this tool needs a straight edge or line")
            return line.points[0], line.points[1]
    raise KeyError(f"Unknown edge or line {reference}")


def through_point(start: Point2D, end: Point2D, point: Point2D) -> tuple[Point2D, Point2D]:
    """The segment moved sideways (keeping its length and direction) so its line passes through `point`."""
    shift = Vector2D.between(_foot(point, start, end), point)
    if shift.length <= COORDINATE:
        raise ValueError("The point is on the line itself, so a parallel through it would only copy the line")
    return along(start, shift, 1), along(end, shift, 1)


def _foot(point: Point2D, start: Point2D, end: Point2D) -> Point2D:
    direction = unit(Vector2D.between(start, end))
    offset = Vector2D.between(start, point)
    return along(start, direction, offset.x * direction.x + offset.y * direction.y)


def foot_on_line(point: Point2D, start: Point2D, end: Point2D) -> Point2D:
    """The foot of the perpendicular from `point` to the infinite line through start and end."""
    foot = _foot(point, start, end)
    if Vector2D.between(foot, point).length <= COORDINATE:
        raise ValueError("The point is already on the line, so there is no perpendicular to draw")
    return foot


def crossing(first: tuple[Point2D, Point2D], second: tuple[Point2D, Point2D]) -> Point2D:
    """Where the infinite lines through two segments meet; lines within the angle tolerance count as parallel."""
    along_first, along_second = unit(Vector2D.between(*first)), unit(Vector2D.between(*second))
    met = intersect(first[0], along_first, second[0], along_second)
    if met is None or abs(cross(along_first, along_second)) < sin(radians(ANGLE_DEGREES)):
        raise ValueError("The lines are parallel, so they do not intersect")
    return met
