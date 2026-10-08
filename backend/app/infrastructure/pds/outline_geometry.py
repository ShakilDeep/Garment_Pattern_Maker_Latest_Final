"""Shapely measurements of a reference piece outline (fold halves are unioned into one piece)."""
from shapely import union_all
from shapely.geometry import Polygon

from app.domain.reference import PieceOutline

CM2_PER_M2 = 10_000.0


def _cut_shape(outline: PieceOutline):
    return union_all([Polygon(ring) for ring in outline.cut])


def area_m2(outline: PieceOutline) -> float:
    return _cut_shape(outline).area / CM2_PER_M2


def bounds_cm(outline: PieceOutline) -> tuple[float, float, float, float]:
    """(min_x, min_y, max_x, max_y) in cm, measured as Optitex's SIZE_X/SIZE_Y are.

    AREA covers the whole piece, but the size of a piece cut on the fold is its half's size.
    """
    min_x, min_y, max_x, max_y = Polygon(outline.cut[0]).bounds
    return min_x, min_y, max_x, max_y
