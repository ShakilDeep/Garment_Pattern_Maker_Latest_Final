"""Every block's draft as V6 pieces (Adapter, T129): named blocks draft them directly; the V5 demo shirt
goes through the drafting engine's Strangler Fig adapter and keeps its adapter ids (p0, s0…), as its V5
draft has no names.
"""
from collections.abc import Mapping

from app.application.drafting_engine import draft
from app.domain.blocks.base import Block, NamedBlock, Pieces
from app.domain.blocks.run import draft_named


def draft_block_pieces(
    block: Block, measurements: Mapping[str, float], size: str, requested: Mapping[str, str]
) -> Pieces:
    if isinstance(block, NamedBlock):
        return draft_named(block, measurements, size, requested)
    return draft(block, measurements, size, requested).pieces
