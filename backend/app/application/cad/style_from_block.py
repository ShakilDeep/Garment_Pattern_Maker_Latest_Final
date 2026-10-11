"""A V6 style drafted straight from a block that ships its reference measurement sets (T130, T131).

The 1078375 block carries its PDS-derived base size and its graded sizes (docs/grading/shirt.md), so its
style holds every size, each drafted from its own measurements (re-drafted, not delta-graded). Every piece
gets the block's own per-edge seam allowance. A block without reference sets (the V5 demo shirt) is drafted
through a project instead.
"""
from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol, runtime_checkable

from app.application.block_pieces import draft_block_pieces
from app.application.cad.style_ids import new_style_id
from app.domain.blocks.base import NamedBlock
from app.domain.blocks.registry import installed
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style


@runtime_checkable
class ReferenceBlock(NamedBlock, Protocol):
    reference_size: str

    def reference_measurements(self) -> Mapping[str, float]:
        """The measurement set the block was derived from, at ``reference_size``."""
        ...

    def graded_sizes(self) -> tuple[str, ...]:
        """Every size the block has a measurement set for, in order (it includes ``reference_size``)."""
        ...

    def graded_measurements(self, size: str) -> Mapping[str, float]:
        """The measurement set of one graded size."""
        ...

    def seam_allowance(self, piece_id: object) -> SeamAllowance:
        """The piece's per-edge seam allowance from the block's finishing settings."""
        ...


def style_from_block(block_id: str) -> Style:
    block = installed().get(block_id)
    if not isinstance(block, ReferenceBlock):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"Block {block_id} has no reference measurement set; draft it through a project")  # noqa: TRY004
    sizes, base = block.graded_sizes(), block.reference_size
    geometry = {size: SizePieces.from_pieces(draft_block_pieces(block, block.graded_measurements(size), size, {}))
                for size in sizes}
    style_id = new_style_id()
    style = Style(style_id, f"{block.id} {sizes[0]}-{sizes[-1]}", sizes, base, geometry)
    return replace(style, allowances={pid: block.seam_allowance(pid) for pid in style.piece_ids})
