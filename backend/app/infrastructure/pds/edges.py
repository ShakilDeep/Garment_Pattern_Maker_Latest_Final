"""Measure a PDS piece's seam allowance edge by edge: the cut line split at its corners, each edge's median
distance to the sew line. This is how the finishing settings were seeded and how they are re-checked.
"""
import statistics
from dataclasses import dataclass

from shapely.geometry import LinearRing, LineString

from app.domain.interchange import Point
from app.domain.reference import ReferencePiece
from app.infrastructure.aama.corners import split_vertices

MIN_EDGE_CM = 2.0  # shorter edges are corner rounding, not seams
ON_FOLD_CM = 0.05
SAMPLES = 15  # evenly spaced over the inner 70 % of the edge, away from corner effects
INNER_START = 0.15


@dataclass(frozen=True)
class EdgeAllowance:
    length_cm: float
    mid: Point
    median_cm: float
    on_fold: bool


def _edges(ring: tuple[Point, ...]) -> list[LineString]:
    turns, _ = split_vertices(ring)
    starts = sorted(ring.index(point) for point in turns)
    edges = []
    for start, end in zip(starts, starts[1:] + starts[:1], strict=True):
        points = ring[start:end + 1] if start < end else ring[start:] + ring[:end + 1]
        if len(points) >= 2:
            edges.append(LineString(points))
    return edges


def edge_allowances(piece: ReferencePiece) -> list[EdgeAllowance]:
    """Edges of the first cut half that are at least MIN_EDGE_CM long; fold edges are flagged, not measured."""
    outline = piece.outline
    if not outline.sew:
        return []
    sew = LinearRing(outline.sew[0])
    fold = LineString(outline.folds[0]) if outline.folds else None
    measured = []
    for edge in _edges(outline.cut[0]):
        if edge.length < MIN_EDGE_CM:
            continue
        mid = edge.interpolate(0.5, normalized=True)
        on_fold = fold is not None and fold.distance(mid) <= ON_FOLD_CM
        step = (1 - 2 * INNER_START) / (SAMPLES - 1)
        distances = [sew.distance(edge.interpolate(INNER_START + i * step, normalized=True)) for i in range(SAMPLES)]
        median = 0.0 if on_fold else statistics.median(distances)
        measured.append(EdgeAllowance(round(edge.length, 3), (round(mid.x, 3), round(mid.y, 3)), median, on_fold))
    return measured
