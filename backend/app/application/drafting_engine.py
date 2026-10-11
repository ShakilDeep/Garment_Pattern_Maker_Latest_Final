"""The one drafting engine (T141, Facade + Strategy by block port).

Every draft returns both forms of the same geometry: the V6 pieces that the CAD tools and the Optitex
export read, and the V5 pattern dict that the existing views, markers and exports read. A dict block
drafts V5 natively and its V6 pieces come through the Strangler Fig adapter, so its V5 output stays byte
for byte what it was. A named block drafts V6 natively; its V5 view arrives in T141b.
"""
from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.blocks.base import Block, Pieces
from app.domain.blocks.run import draft_pattern
from app.infrastructure.legacy_pattern_adapter import piece_from_v5


@dataclass(frozen=True)
class Draft:
    pieces: Pieces
    pattern: dict


def draft(block: Block, values: Mapping[str, float], size: str, options: Mapping[str, str]) -> Draft:
    pattern = draft_pattern(block, values, size, options)  # refuses a named block until T141b
    return Draft(tuple(piece_from_v5(piece).piece for piece in pattern["pieces"]), pattern)
