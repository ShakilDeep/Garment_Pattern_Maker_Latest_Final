"""Piece validators for the CAD guard (Chain of Responsibility links). Each returns a refusal or None.

They reuse the PM-03 Shapely checks (`infrastructure/piece_validity.py`), whose messages already name the piece.
"""

from typing import Protocol

from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.piece_validity import check_cut_geometry, check_stitch_outline


class PieceValidator(Protocol):
    def refusal(self, piece: Piece, allowance: SeamAllowance | None) -> str | None: ...


class OutlineValidator:
    """The stitch outline has an area and does not cross or touch itself."""

    def refusal(self, piece: Piece, allowance: SeamAllowance | None) -> str | None:
        try:
            check_stitch_outline(piece)
        except ValueError as exc:
            return str(exc)
        return None


class CutOutlineValidator:
    """With a seam allowance, the cut outline is valid and keeps every edge's full allowance."""

    def refusal(self, piece: Piece, allowance: SeamAllowance | None) -> str | None:
        if allowance is None:
            return None
        try:
            check_cut_geometry(piece, allowance)
        except ValueError as exc:
            return str(exc)
        return None
