"""Read model for an existing CAD pattern used as reference data (build plan M0).

Lengths are centimetres and areas square metres, as stored by Optitex. Outline coordinates are
centimetres with y pointing up; cut rings are counter-clockwise and not explicitly closed.
"""
from collections.abc import Mapping
from dataclasses import dataclass

Point = tuple[float, float]
Polyline = tuple[Point, ...]


@dataclass(frozen=True)
class GeomInfo:
    """One piece in one size: bounding box, cut and sew measurements.

    Sew values are None for a piece without a sew line (e.g. a drawstring cut to size).
    """

    size_x_cm: float
    size_y_cm: float
    area_m2: float
    perimeter_cm: float
    sew_area_m2: float | None
    sew_perimeter_cm: float | None


@dataclass(frozen=True)
class SizeTotals:
    """Totals over every piece of one size, counting piece quantities."""

    area_m2: float
    perimeter_cm: float
    sew_area_m2: float
    sew_perimeter_cm: float


@dataclass(frozen=True)
class PieceOutline:
    """Base-size drawing of one piece; a piece cut on the fold has two mirrored cut halves."""

    cut: tuple[Polyline, ...]
    sew: tuple[Polyline, ...] = ()
    folds: tuple[Polyline, ...] = ()
    notches: tuple[Polyline, ...] = ()


@dataclass(frozen=True)
class ReferencePiece:
    name: str
    code: str
    quantity: int
    on_fold: bool
    rotation_deg: float
    opposite: str
    geometry: Mapping[str, GeomInfo]
    outline: PieceOutline


@dataclass(frozen=True)
class ReferenceStyle:
    name: str
    optitex_version: str
    sizes: tuple[str, ...]
    base_size: str
    totals: Mapping[str, SizeTotals]
    pieces: tuple[ReferencePiece, ...]
