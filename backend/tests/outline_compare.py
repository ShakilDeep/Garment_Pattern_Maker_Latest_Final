"""Outline distance between a drafted V5 piece and a PDS sew outline, for the shape-accuracy tests.

The two are drawn in different frames, so the drafted outline is tried in every quarter turn, mirrored or
not, with its centroid on the PDS one; the best fit's Hausdorff distance (cm) and area ratio are reported.
"""
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.domain.reference import ReferencePiece


@dataclass(frozen=True)
class Fit:
    hausdorff_cm: float
    area_ratio: float  # drafted / PDS
    iou: float


def pds_outline(piece: ReferencePiece) -> Polygon:
    """The whole sew outline; a piece cut on the fold is its two halves joined along the fold."""
    halves = unary_union([Polygon(ring).buffer(0) for ring in piece.outline.sew])
    return halves.buffer(0.01).buffer(-0.01)


def above(outline: Polygon, depth: float, top_at_max_x: bool = False) -> Polygon:
    """The part within ``depth`` of the top: min y for a drafted piece, max x for a PDS sleeve."""
    x0, y0, x1, y1 = outline.bounds
    return outline.intersection(box(x1 - depth, y0, x1, y1) if top_at_max_x else box(x0, y0, x1, y0 + depth))


def fit(drafted: Polygon, pds: Polygon) -> Fit:
    found = None
    for mirror in (1, -1):
        for angle in (0, 90, 180, 270):
            turned = affinity.rotate(affinity.scale(drafted, mirror, 1, origin=(0, 0)), angle, origin=(0, 0))
            moved = affinity.translate(turned, pds.centroid.x - turned.centroid.x, pds.centroid.y - turned.centroid.y)
            distance = moved.hausdorff_distance(pds)
            if found is None or distance < found[0]:
                found = (distance, moved)
    distance, moved = found
    return Fit(distance, drafted.area / pds.area, moved.intersection(pds).area / moved.union(pds).area)


def piece_fit(points: list, pds: ReferencePiece) -> Fit:
    return fit(Polygon(points).buffer(0), pds_outline(pds))
