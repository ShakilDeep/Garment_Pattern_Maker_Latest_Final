"""Outline distance between a drafted piece and a PDS sew outline (shape accuracy, spec §7 gap limits).

The two are drawn in different frames, so the drafted outline is tried in every quarter turn, mirrored or
not, with its centroid on the PDS one; the best fit's Hausdorff distance (cm) and area ratio are reported.
"""
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.domain.reference import ReferencePiece

QUARTER_TURNS = (0, 90, 180, 270)
MIRRORS = (1, -1)
SEAL_CM = 0.01  # closes the hairline gap between the two halves of a fold piece's PDS outline


@dataclass(frozen=True)
class Fit:
    hausdorff_cm: float
    area_ratio: float  # drafted / PDS
    iou: float


def pds_outline(piece: ReferencePiece) -> Polygon:
    """The whole sew outline; a piece cut on the fold is its two halves joined along the fold."""
    halves = unary_union([Polygon(ring).buffer(0) for ring in piece.outline.sew])
    return halves.buffer(SEAL_CM).buffer(-SEAL_CM)


def above(outline: Polygon, depth: float, top_at_max_x: bool = False) -> Polygon:
    """The part within ``depth`` of the top: min y for a drafted piece, max x for a PDS sleeve."""
    x0, y0, x1, y1 = outline.bounds
    return outline.intersection(box(x1 - depth, y0, x1, y1) if top_at_max_x else box(x0, y0, x1, y0 + depth))


def _placed(drafted: Polygon, pds: Polygon, mirror: int, angle: int) -> Polygon:
    turned = affinity.rotate(affinity.scale(drafted, mirror, 1, origin=(0, 0)), angle, origin=(0, 0))
    return affinity.translate(turned, pds.centroid.x - turned.centroid.x, pds.centroid.y - turned.centroid.y)


def fit(drafted: Polygon, pds: Polygon) -> Fit:
    placements = (_placed(drafted, pds, mirror, angle) for mirror in MIRRORS for angle in QUARTER_TURNS)
    best = min(placements, key=pds.hausdorff_distance)
    iou = best.intersection(pds).area / best.union(pds).area
    return Fit(best.hausdorff_distance(pds), drafted.area / pds.area, iou)
