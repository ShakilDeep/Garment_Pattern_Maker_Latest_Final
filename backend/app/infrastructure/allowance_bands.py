"""The allowance a cut outline must keep (PM-03 guard): the stitch shape plus every edge's full-width band.

Bands follow the stitch sub-segments of each edge. At the edge's own end points they use the true tangent
normal, exactly as the cut line is built there, so sampled curves are not mistaken for lost allowance. Each
band is the convex hull of its corners, so a sub-segment shorter than the tangent/chord gap cannot twist it.
Band ends at fold-back, reverse and fold corners are not required: those corners shape or trim them.
"""

from dataclasses import dataclass
from itertools import pairwise

from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

from app.domain.geom.lines import along, unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.cut_outline import edge_widths
from app.domain.pattern.edges import edge_polylines, edge_tangents, stitch_ring
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance

SHAPED = (CornerStyle.FOLD_BACK, CornerStyle.REVERSE)


def _outwards(direction: Vector2D, side: int) -> Vector2D:
    return Vector2D(direction.y * side, -direction.x * side)


def _shaped_corners(piece: Piece, allowance: SeamAllowance) -> list[bool]:
    """Per outline edge: is the corner at its end shaped by its style or by the fold line?"""
    fold = piece.fold.segment if piece.fold else None
    count = len(piece.outline)
    return [
        allowance.style_at(s.end) in SHAPED or fold in (s.id, piece.outline[(i + 1) % count].id)
        for i, s in enumerate(piece.outline)
    ]


@dataclass(frozen=True)
class _EdgeBand:
    polyline: tuple[Point2D, ...]
    ends: tuple[Vector2D, Vector2D]  # true unit tangents at the edge's start and end
    width: float
    skip: tuple[bool, bool]  # leave out the band end at the start / end corner


def _edge_bands(edge: _EdgeBand, side: int) -> list[Polygon]:
    pairs = [(a, b) for a, b in pairwise(edge.polyline) if a != b]
    bands = []
    for k, (a, b) in enumerate(pairs):
        first, last = k == 0, k == len(pairs) - 1
        if (first and edge.skip[0]) or (last and edge.skip[1]):
            continue
        chord = unit(Vector2D.between(a, b))
        normal_a = _outwards(edge.ends[0] if first else chord, side)
        normal_b = _outwards(edge.ends[1] if last else chord, side)
        corners = (a, b, along(b, normal_b, edge.width), along(a, normal_a, edge.width))
        hull = MultiPoint([(p.x, p.y) for p in corners]).convex_hull  # never a twisted (bow-tie) quad
        if isinstance(hull, Polygon):
            bands.append(hull)
    return bands


def required_region(piece: Piece, allowance: SeamAllowance, side: int) -> Polygon:
    shaped = _shaped_corners(piece, allowance)
    parts = [Polygon([(p.x, p.y) for p in stitch_ring(piece)])]
    edges = zip(edge_polylines(piece), edge_tangents(piece), edge_widths(piece, allowance))
    for index, (polyline, ends, width) in enumerate(edges):
        if width > 0:
            parts += _edge_bands(_EdgeBand(polyline, ends, width, (shaped[index - 1], shaped[index])), side)
    return unary_union(parts)
