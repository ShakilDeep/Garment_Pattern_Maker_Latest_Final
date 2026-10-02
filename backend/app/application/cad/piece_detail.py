"""What the editor shows for one piece of one size: the piece, its seam allowance, cut outline and hash."""

from dataclasses import dataclass

from app.domain.geom.primitives import Point2D
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.ids import PieceId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.style import Style
from app.infrastructure.piece_validity import check_cut_geometry


@dataclass(frozen=True)
class PieceDetail:
    style_id: str
    size: str
    piece: Piece
    geometry_hash: str
    allowance: SeamAllowance | None
    cut_outline: tuple[Point2D, ...] | None  # None while the piece has no seam allowance


def piece_detail(style: Style, piece_id: str, size: str) -> PieceDetail:
    """KeyError (404) for an unknown size or piece; ValueError (400) for a size that has no pieces yet."""
    wanted = PieceId(piece_id)
    piece = next((p for p in style.view(size) if p.id == wanted), None)
    if piece is None:
        raise KeyError(f"Unknown piece {piece_id}")
    allowance = style.allowances.get(wanted)
    cut = None if allowance is None else check_cut_geometry(piece, allowance)
    return PieceDetail(str(style.id), size, piece, geometry_hash(piece), allowance, cut)
