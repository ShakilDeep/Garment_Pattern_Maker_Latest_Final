"""Shapely checks for PM-03: the stitch outline is a simple shape and its cut outline is valid and complete.

Refused here with a ValueError (400 when called directly; the CAD guard reports it as 422 GEOMETRY_INVALID):
- stitch outlines with zero area (collinear points, opposite arcs) or that revisit a position, the cases
  doc 108 deferred from P1-01;
- cut outlines that are invalid or lose allowance: the cut must cover the stitch line and every edge's band
  (its full width beside each stitch sub-segment), except at corners a fold-back or reverse style shapes or
  the fold line trims.
"""

import logging

from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.validation import explain_validity

from app.domain.geom.primitives import Point2D
from app.domain.pattern.cut_outline import offset_ring
from app.domain.pattern.edges import orientation, stitch_ring
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.domain.tolerances import LENGTH_CM
from app.infrastructure.allowance_bands import required_region
from app.infrastructure.cut_envelope import envelope


def _polygon(ring: tuple[Point2D, ...]) -> Polygon:
    return Polygon([(p.x, p.y) for p in ring])


def _stitch_side(piece: Piece) -> int:
    ring = stitch_ring(piece)
    try:
        side = orientation(ring)
    except ValueError as exc:
        raise ValueError(f"{piece.name}: {exc}") from exc
    stitch = _polygon(ring)
    if not stitch.is_valid:
        raise ValueError(f"{piece.name}: the outline is not a simple outline ({explain_validity(stitch)})")
    return side


def check_stitch_outline(piece: Piece) -> None:
    """Refuse a stitch outline with zero area or that is not simple (crosses or touches itself)."""
    _stitch_side(piece)


def _checked_cut(piece: Piece, allowance: SeamAllowance, side: int) -> tuple[Point2D, ...]:
    cut = envelope(offset_ring(piece, allowance))
    shape = _polygon(cut)
    if not shape.is_valid:
        raise ValueError(f"the seam allowance produced an invalid cut outline ({explain_validity(shape)})")
    missing = required_region(piece, allowance, side).difference(shape.buffer(LENGTH_CM))
    if not missing.is_empty:
        near = missing.representative_point()
        raise ValueError(f"the seam allowance produced an invalid cut outline "
                         f"({missing.area:.4f} cm² of allowance lost near ({near.x:.2f}, {near.y:.2f}))")
    return cut


def check_cut_geometry(piece: Piece, allowance: SeamAllowance) -> tuple[Point2D, ...]:
    """The validated cut outline as an open ring wound like the stitch outline."""
    side = _stitch_side(piece)
    try:
        return _checked_cut(piece, allowance, side)
    except GEOSException as exc:  # a geometry engine failure is still a refused piece, never a 500
        logging.getLogger("garment").warning("Cut outline engine failure for %s: %s", piece.id, exc)
        message = f"{piece.name}: the cut outline could not be computed for this seam allowance"
        raise ValueError(message) from exc
    except ValueError as exc:
        raise ValueError(f"{piece.name}: {exc}") from exc
