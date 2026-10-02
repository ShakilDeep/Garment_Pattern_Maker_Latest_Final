"""The piece of one size a piece-level draft tool edits: find it, change it, put it back (KeyError if absent)."""

from collections.abc import Callable
from dataclasses import dataclass

from app.application.cad.command import Params
from app.application.cad.tools_draft.params import text
from app.domain.pattern.ids import PieceId
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style

TARGET_PARAMS = ("size", "piece_id")


@dataclass(frozen=True)
class PieceTarget:
    size: str
    piece_id: PieceId

    @classmethod
    def of(cls, params: Params) -> "PieceTarget":
        return cls(text(params, "size"), PieceId(text(params, "piece_id")))

    def edit(self, style: Style, change: Callable[[Piece], Piece]) -> Style:
        piece = next((p for p in style.view(self.size) if p.id == self.piece_id), None)
        if piece is None:
            raise KeyError(f"Unknown piece {self.piece_id}")
        return style.with_piece(self.size, change(piece))
