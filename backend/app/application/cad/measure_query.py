"""The measure tool's query (CAD-05): one measurement of one piece of one size, computed here, never in the UI.

Kinds: ``distance`` between two points, ``path`` length over edges, ``angle`` at a point, and ``area`` or
``perimeter`` of the sew outline (dense curves) or the cut outline (the validated seam-allowance outline).
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.application.cad.piece_detail import piece_detail
from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.measure import angle_at, dense_ring, distance, path_length, ring_area, ring_perimeter
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style

MeasureKind = Literal["distance", "path", "angle", "area", "perimeter"]
POINT_PAIR = 2


@dataclass(frozen=True)
class MeasureRequest:
    kind: MeasureKind
    points: tuple[str, ...] = ()
    edges: tuple[str, ...] = ()
    point: str | None = None
    outline: Literal["sew", "cut"] = "sew"


@dataclass(frozen=True)
class Measurement:
    kind: MeasureKind
    value: float
    unit: Literal["cm", "deg", "cm2"]


def _ring(style: Style, piece: Piece, size: str, outline: str) -> Sequence[Point2D]:
    if outline == "sew":
        return dense_ring(piece)
    detail = piece_detail(style, str(piece.id), size)
    if detail.cut_outline is None:
        raise ValueError(f"{detail.piece.name} has no seam allowance, so it has no cut outline")
    return detail.cut_outline


def _piece(style: Style, size: str, piece_id: str) -> Piece:
    found = next((p for p in style.view(size) if str(p.id) == piece_id), None)
    if found is None:
        raise KeyError(f"Unknown piece {piece_id}")
    return found


def measure(style: Style, size: str, piece_id: str, request: MeasureRequest) -> Measurement:
    piece = _piece(style, size, piece_id)
    if request.kind == "distance":
        if len(request.points) != POINT_PAIR:
            raise ValueError("A distance needs exactly two points")
        return Measurement("distance", distance(piece, *map(PointId, request.points)), "cm")
    if request.kind == "path":
        return Measurement("path", path_length(piece, [SegmentId(e) for e in request.edges]), "cm")
    if request.kind == "angle":
        if request.point is None:
            raise ValueError("An angle needs a point")
        return Measurement("angle", angle_at(piece, PointId(request.point)), "deg")
    ring = _ring(style, piece, size, request.outline)
    if request.kind == "area":
        return Measurement("area", ring_area(ring), "cm2")
    return Measurement("perimeter", ring_perimeter(ring), "cm")
