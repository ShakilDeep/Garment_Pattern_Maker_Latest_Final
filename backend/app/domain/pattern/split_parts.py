"""The two segments one segment splits into, and the one segment two segments join into (per segment type)."""

from math import atan, pi

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.notch_position import point_on
from app.domain.pattern.resolve import arc_from_bulge
from app.domain.pattern.segment import Arc, CubicBezier, Line, Segment
from app.domain.pattern.subdivide import Quad, merged_bulge, merged_cubic, split_bulge, split_cubic
from app.domain.tolerances import LENGTH_CM

Positions = dict[PointId, Point2D]
FULL_TURN = 2 * pi  # a joined arc must stay short of a full circle
NOT_ONE_SHAPE = "do not continue one line, arc or curve, so joining them would change the outline"


def _quad(segment: CubicBezier, positions: Positions) -> Quad:
    a, d = positions[segment.start], positions[segment.end]
    h, k = segment.start_handle, segment.end_handle
    return a, Point2D(a.x + h.x, a.y + h.y), Point2D(d.x + k.x, d.y + k.y), d


def _cubic(segment_id: SegmentId, ends: tuple[PointId, PointId], quad: Quad) -> CubicBezier:
    a, b, c, d = quad
    return CubicBezier(segment_id, *ends, Vector2D.between(a, b), Vector2D.between(d, c))


def split_parts(
    segment: Segment, positions: Positions, t: float, point: PointId, new_id: SegmentId
) -> tuple[Segment, Segment]:
    first_ends, second_ends = (segment.start, point), (point, segment.end)
    if isinstance(segment, CubicBezier):
        left, right = split_cubic(_quad(segment, positions), t)
        return _cubic(segment.id, first_ends, left), _cubic(new_id, second_ends, right)
    if isinstance(segment, Arc):
        first_bulge, second_bulge = split_bulge(segment.bulge, t)
        return Arc(segment.id, *first_ends, first_bulge), Arc(new_id, *second_ends, second_bulge)
    return Line(segment.id, *first_ends), Line(new_id, *second_ends)


def _joined_lines(first: Line, second: Line, positions: Positions) -> tuple[Segment, float]:
    a, m, b = positions[first.start], positions[first.end], positions[second.end]
    chord, to_middle = Vector2D.between(a, b), Vector2D.between(a, m)
    along = (chord.x * to_middle.x + chord.y * to_middle.y) / (chord.length ** 2)
    off_line = abs(chord.x * to_middle.y - chord.y * to_middle.x) / chord.length
    if off_line > LENGTH_CM or not 0 < along < 1:
        raise ValueError(f"Edges {first.id} and {second.id} {NOT_ONE_SHAPE}")
    return Line(first.id, first.start, second.end), along


def _joined_arcs(first: Arc, second: Arc, positions: Positions) -> tuple[Segment, float]:
    """One circle: the merged arc must pass through the shared point and both halves' middles (LENGTH_CM).

    Comparing points rather than centres keeps shallow arcs joinable: their centres move a lot per bulge
    quantum.
    """
    turned = abs(4 * atan(first.bulge)) + abs(4 * atan(second.bulge))
    if (first.bulge > 0) != (second.bulge > 0) or turned >= FULL_TURN:
        raise ValueError(f"Edges {first.id} and {second.id} {NOT_ONE_SHAPE}")
    bulge, share = merged_bulge(first.bulge, second.bulge)
    a, m, b = positions[first.start], positions[first.end], positions[second.end]
    merged = arc_from_bulge(a, b, bulge)
    checks = ((share, m), (share / 2, point_on(arc_from_bulge(a, m, first.bulge), 0.5)),
              ((1 + share) / 2, point_on(arc_from_bulge(m, b, second.bulge), 0.5)))
    if any(Vector2D.between(point_on(merged, t), expected).length > LENGTH_CM for t, expected in checks):
        raise ValueError(f"Edges {first.id} and {second.id} {NOT_ONE_SHAPE}")
    return Arc(first.id, first.start, second.end, bulge), share


def joined_parts(first: Segment, second: Segment, positions: Positions) -> tuple[Segment, float]:
    """The joined segment (keeping the first id) and the first part's share of its parameter range."""
    if isinstance(first, Line) and isinstance(second, Line):
        return _joined_lines(first, second, positions)
    if isinstance(first, Arc) and isinstance(second, Arc):
        return _joined_arcs(first, second, positions)
    if isinstance(first, CubicBezier) and isinstance(second, CubicBezier):
        merged = merged_cubic(_quad(first, positions), _quad(second, positions))
        if merged is not None:
            quad, share = merged
            return _cubic(first.id, (first.start, second.end), quad), share
    raise ValueError(f"Edges {first.id} and {second.id} {NOT_ONE_SHAPE}")
