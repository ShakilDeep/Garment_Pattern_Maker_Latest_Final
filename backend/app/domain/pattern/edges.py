"""A piece's outline as polylines, one per segment (curves sampled), plus its orientation."""

from app.domain.geom.primitives import LineSegment, Point2D, Vector2D
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Segment
from app.domain.pattern.tangents import end_tangents
from app.domain.tolerances import COORDINATE


def edge_polyline(segment: Segment, positions: dict) -> tuple[Point2D, ...]:
    """Start to end of one outline segment; sampled curves keep their exact end points."""
    start, end = positions[segment.start], positions[segment.end]
    curve = resolve_segment(segment, positions)
    if isinstance(curve, LineSegment):
        return (start, end)
    return (start, *curve.sample()[1:-1], end)


def edge_polylines(piece: Piece) -> tuple[tuple[Point2D, ...], ...]:
    positions = {p.id: p.position for p in piece.points}
    return tuple(edge_polyline(segment, positions) for segment in piece.outline)


def edge_tangents(piece: Piece) -> tuple[tuple[Vector2D, Vector2D], ...]:
    """Each outline segment's true unit tangents at its start and end."""
    positions = {p.id: p.position for p in piece.points}
    return tuple(
        end_tangents(resolve_segment(s, positions), positions[s.start], positions[s.end])
        for s in piece.outline
    )


def stitch_ring(piece: Piece) -> tuple[Point2D, ...]:
    """The stitch (seam) line as an open ring of points in outline order."""
    return tuple(point for polyline in edge_polylines(piece) for point in polyline[:-1])


def orientation(ring: tuple[Point2D, ...]) -> int:
    """+1 for a counter-clockwise ring, -1 for clockwise; a ring that encloses no area is refused."""
    twice_area = sum(a.x * b.y - b.x * a.y for a, b in zip(ring, (*ring[1:], ring[0])))
    if abs(twice_area) / 2 <= COORDINATE:
        raise ValueError("The outline encloses zero area")
    return 1 if twice_area > 0 else -1
