"""A drafting block: one garment family's draft (Strategy), its POMs, style options and calibration status."""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.blocks.transforms import Transform

Calibration = Literal["demo", "client_approved"]


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


class Block(Protocol):
    id: str
    version: str
    family: str
    calibration: Calibration
    required: tuple[str, ...]
    optional: tuple[str, ...]
    options: tuple[StyleOption, ...]
    transforms: tuple[Transform, ...]

    def draft(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> dict:
        """The base pattern for one size; transforms then apply the chosen style options."""
        ...
