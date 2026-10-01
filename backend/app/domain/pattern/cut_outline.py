"""Raw cut ring (PM-03): each outline edge offset outwards by its own allowance, joined per corner style.

Curves are offset as their sampled polylines with mitred sub-joins; corners use the curves' true end
tangents. The fold edge always gets no allowance. The raw ring may cross itself where a concave stretch
curves tighter than its allowance or a slit is narrower than two allowances: infrastructure.cut_envelope
resolves it to the cut outline and infrastructure.piece_validity checks the result.
"""

from dataclasses import dataclass
from itertools import pairwise

from app.domain.geom.lines import along, cross, intersect, unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.corner_join import CornerJoin
from app.domain.pattern.corners import join_corner, join_fold
from app.domain.pattern.edges import edge_polylines, edge_tangents, orientation, stitch_ring
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import quantize
from app.domain.pattern.seam import SeamAllowance


@dataclass(frozen=True)
class _Edge:
    points: tuple[Point2D, ...]
    directions: tuple[Vector2D, ...]
    width: float
    side: int

    def shifted(self, point: Point2D, direction: Vector2D) -> Point2D:
        """The point moved outwards (right of travel for a counter-clockwise ring) by this edge's width."""
        return along(point, Vector2D(direction.y * self.side, -direction.x * self.side), self.width)


def _edge(polyline: tuple[Point2D, ...], width: float, side: int) -> _Edge:
    points = tuple(p for i, p in enumerate(polyline) if i == 0 or p != polyline[i - 1])
    directions = tuple(unit(Vector2D.between(a, b)) for a, b in pairwise(points))
    return _Edge(points, directions, width, side)


def _interior(edge: _Edge) -> list[Point2D]:
    """Sub-joins inside a sampled curve: mitred where it bends outwards, back through the vertex inwards."""
    joins: list[Point2D] = []
    for k in range(1, len(edge.points) - 1):
        before, after = edge.directions[k - 1], edge.directions[k]
        end, start = edge.shifted(edge.points[k], before), edge.shifted(edge.points[k], after)
        met = intersect(end, before, start, after)
        if met is None or cross(before, after) * edge.side < 0:
            joins.extend([end, edge.points[k], start] if met is not None else [end, start])
        else:
            joins.append(met)
    return joins


def edge_widths(piece: Piece, allowance: SeamAllowance) -> list[float]:
    """Each outline edge's allowance in cm (the fold edge gets 0); ids the piece does not have raise."""
    segments, corners = {s.id for s in piece.outline}, {s.end for s in piece.outline}
    unknown = sorted(str(key) for key, _ in allowance.edge_widths if key not in segments)
    if unknown:
        raise ValueError(f"{piece.name}: seam allowance names unknown segment {', '.join(unknown)}")
    loose = sorted(str(key) for key, _ in allowance.corner_styles if key not in corners)
    if loose:
        raise ValueError(f"{piece.name}: seam allowance names unknown corner {', '.join(loose)}")
    fold = piece.fold.segment if piece.fold else None
    if fold is not None and dict(allowance.edge_widths).get(fold, 0) > 0:
        raise ValueError(f"{piece.name}: the fold edge {fold} gets no seam allowance")
    return [0.0 if s.id == fold else allowance.width_of(s.id) for s in piece.outline]


def _clean(ring: list[Point2D]) -> tuple[Point2D, ...]:
    points = [Point2D(quantize(p.x), quantize(p.y)) for p in ring]
    kept = [p for i, p in enumerate(points) if p != points[i - 1]] if len(set(points)) > 1 else points[:1]
    return tuple(kept)


def offset_ring(piece: Piece, allowance: SeamAllowance) -> tuple[Point2D, ...]:
    """The raw cut ring as open points, starting at the first edge's far corner (may cross itself)."""
    side = orientation(stitch_ring(piece))
    widths = edge_widths(piece, allowance)
    edges = [_edge(polyline, width, side) for polyline, width in zip(edge_polylines(piece), widths)]
    tangents = edge_tangents(piece)
    fold = piece.fold.segment if piece.fold else None
    ring: list[Point2D] = []
    for index, edge in enumerate(edges):
        following = (index + 1) % len(edges)
        vertex, in_dir, out_dir = edge.points[-1], tangents[index][1], tangents[following][0]
        corner = CornerJoin(vertex, in_dir, out_dir, edge.shifted(vertex, in_dir),
                            edges[following].shifted(vertex, out_dir), edge.width, edges[following].width)
        style = allowance.style_at(piece.outline[index].end)
        at_fold = fold in (piece.outline[index].id, piece.outline[following].id)
        joined = join_fold(corner, side) if at_fold else join_corner(corner, style, side)
        curved = (len(edge.points) > 2, len(edges[following].points) > 2)
        ring += _interior(edge) + list(corner.framed(joined, curved))
    return _clean(ring)
