"""Outline distance between a drafted V5 piece and a PDS sew outline, for the shape-accuracy tests."""
from shapely.geometry import Polygon

from app.domain.reference import ReferencePiece
from app.infrastructure.outline_fit import Fit, above, fit, pds_outline

__all__ = ["Fit", "above", "fit", "pds_outline", "piece_fit"]


def piece_fit(points: list, pds: ReferencePiece) -> Fit:
    return fit(Polygon(points).buffer(0), pds_outline(pds))
