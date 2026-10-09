"""Adapter: the app's own V5 pattern dict -> InterchangeStyle for DXF-AAMA export.

V5 pieces are drawn whole (fold pieces already unfolded), y pointing down, with closed rings that repeat the
first point. Here y is negated (as in the AutoCAD export) and the closing duplicate dropped; nothing else
changes. ``cut_points`` is the cut line when present, with ``points`` as the sew line; otherwise ``points``
is the cut line and the piece has no sew line.
"""
from collections.abc import Sequence

from app.domain.interchange import InterchangePiece, InterchangeStyle, Point, Ring


def _point(raw: Sequence[float]) -> Point:
    return float(raw[0]) + 0.0, -float(raw[1]) + 0.0


def _ring(raw: Sequence[Sequence[float]]) -> Ring:
    points = tuple(_point(p) for p in raw)
    return points[:-1] if len(points) > 1 and points[0] == points[-1] else points


def _piece(piece: dict, size: str) -> InterchangePiece:
    has_cut = "cut_points" in piece
    grainline = piece.get("grainline")  # absent or null: exported without grain, never invented
    return InterchangePiece(
        name=piece["name"], size=size, quantity=int(piece["quantity"]),
        cut=_ring(piece["cut_points"] if has_cut else piece["points"]),
        sew=(_ring(piece["points"]),) if has_cut else (),
        notches=tuple((_point(notch),) for notch in piece.get("notches", [])),
        grain=(_point(grainline[0]), _point(grainline[-1])) if grainline else None,
    )


def pattern_to_interchange(pattern: dict, style_name: str) -> InterchangeStyle:
    size = pattern["size"]
    return InterchangeStyle(name=style_name, sample_size=size,
                            pieces=tuple(_piece(piece, size) for piece in pattern["pieces"]))
