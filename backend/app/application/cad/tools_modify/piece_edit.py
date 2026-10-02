"""A modify-tool Command: a named, validated change applied to one piece of one size."""

from collections.abc import Callable
from dataclasses import dataclass

from app.application.cad.tools_draft.target import PieceTarget
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class PieceEdit:
    target: PieceTarget
    change: Callable[[Piece], Piece]
    name: str

    def apply(self, state: Style) -> Style:
        return self.target.edit(state, self.change)
