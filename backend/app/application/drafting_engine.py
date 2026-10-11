"""The one drafting engine (T141, Facade + Strategy by block port).

Every draft returns both forms of the same geometry: the V6 pieces that the CAD tools and the Optitex
export read, and the V5 pattern dict that the existing views, markers and exports read. A dict block
drafts V5 natively and its V6 pieces come through the Strangler Fig adapter, so its V5 output stays byte
for byte what it was. A named block drafts V6 natively, with its own per-piece seam allowances, and its V5
dict is a view drawn from those pieces (`infrastructure/v5_view`).
"""
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.domain.blocks.base import Block, NamedBlock, Pieces
from app.domain.blocks.run import draft_named, draft_pattern
from app.domain.pattern.ids import PieceId
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.legacy_pattern_adapter import piece_from_v5
from app.infrastructure.v5_view.pattern_view import pattern_view
from app.infrastructure.v5_view.piece_view import piece_view

Allowances = Mapping[PieceId, SeamAllowance]


@dataclass(frozen=True)
class Draft:
    pieces: Pieces
    pattern: dict
    allowances: Allowances = field(default_factory=dict)  # per piece, for named blocks only


def _allowances(block: NamedBlock, pieces: Pieces) -> Allowances:
    allowance = getattr(block, "seam_allowance", None)
    if allowance is None:  # never guessed: a block without its own allowances cannot be cut
        raise ValueError(f"Block {block.id} has no seam allowances, so its pieces cannot be cut")
    return {piece.id: allowance(piece.id) for piece in pieces}


def draft(block: Block, values: Mapping[str, float], size: str, options: Mapping[str, str]) -> Draft:
    if isinstance(block, NamedBlock):
        pieces = draft_named(block, values, size, options)
        allowances = _allowances(block, pieces)
        views = [piece_view(piece, allowances[piece.id]) for piece in pieces]
        return Draft(pieces, pattern_view(block, values, size, views), allowances)
    pattern = draft_pattern(block, values, size, options)
    return Draft(tuple(piece_from_v5(piece).piece for piece in pattern["pieces"]), pattern)
