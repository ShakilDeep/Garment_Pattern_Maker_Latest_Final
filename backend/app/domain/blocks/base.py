"""A drafting block: one garment family's draft (Strategy), its POMs, style options and calibration status.

Two drafting strategies (T129):
- ``DictBlock`` drafts the V5 pattern dict. Only the demo shirt does, and it reaches the V6 model through
  the legacy adapter with adapter ids (p0, s0…).
- ``NamedBlock`` drafts V6 ``Piece``s whose every point has a drafting name (``sketch.naming``) and whose
  curves are cubic Béziers between named points. Every client block must be one.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from app.domain.blocks.transforms import Transform
from app.domain.pattern.piece import Piece

Calibration = Literal["demo", "client_approved"]
Pieces = tuple[Piece, ...]


@dataclass(frozen=True)
class StyleOption:
    """One choice a style makes on a block (yoke, placket, pocket…); ``fixed`` means the block has no other."""

    id: str
    label: str
    choices: tuple[str, ...]
    default: str
    fixed: bool = False

    def __post_init__(self) -> None:
        if self.default not in self.choices:
            raise ValueError(f"Style option {self.id} default {self.default} is not one of its choices")


class BlockInfo(Protocol):
    id: str
    version: str
    family: str
    calibration: Calibration
    required: tuple[str, ...]
    optional: tuple[str, ...]
    options: tuple[StyleOption, ...]


@runtime_checkable
class DictBlock(BlockInfo, Protocol):
    transforms: tuple[Transform[dict], ...]

    def draft(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> dict:
        """The base V5 pattern dict for one size; transforms then apply the chosen style options."""
        ...


@runtime_checkable
class NamedBlock(BlockInfo, Protocol):
    transforms: tuple[Transform[Pieces], ...]

    def draft_pieces(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> Pieces:
        """The base pieces for one size, every point named; transforms then apply the style options."""
        ...


Block = DictBlock | NamedBlock
