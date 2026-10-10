"""A V6 style drafted straight from a block that ships a reference measurement set (T130).

The 1078375 block carries its PDS-derived size L set, so its style holds that one size until grading (T131).
Every piece gets the block's own per-edge seam allowance. A block without a reference set (the V5 demo
shirt) is drafted through a project instead.
"""
from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol, runtime_checkable
from uuid import uuid4

from app.application.block_pieces import draft_block_pieces
from app.domain.blocks.base import NamedBlock
from app.domain.blocks.registry import installed
from app.domain.pattern.ids import StyleId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style

STYLE_ID_HEX = 12


@runtime_checkable
class ReferenceBlock(NamedBlock, Protocol):
    reference_size: str

    def reference_measurements(self) -> Mapping[str, float]:
        """The measurement set the block was derived from, at ``reference_size``."""
        ...

    def seam_allowance(self, piece_id: object) -> SeamAllowance:
        """The piece's per-edge seam allowance from the block's finishing settings."""
        ...


def style_from_block(block_id: str) -> Style:
    block = installed().get(block_id)
    if not isinstance(block, ReferenceBlock):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"Block {block_id} has no reference measurement set; draft it through a project")  # noqa: TRY004
    size = block.reference_size
    pieces = draft_block_pieces(block, block.reference_measurements(), size, {})
    style_id = StyleId(f"style-{uuid4().hex[:STYLE_ID_HEX]}")
    style = Style(style_id, f"{block.id} {size}", (size,), size, {size: SizePieces.from_pieces(pieces)})
    return replace(style, allowances={piece.id: block.seam_allowance(piece.id) for piece in pieces})
