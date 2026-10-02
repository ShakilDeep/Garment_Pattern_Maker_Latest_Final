"""Per-piece canonical Memento texts with their SHA-256 digests (the command history's chunks), built once."""

import json
from collections.abc import Iterable

from app.domain.pattern.canonical import canonical_dumps, text_digest
from app.domain.pattern.piece import Piece
from app.domain.pattern.serialize import piece_to_data


class PieceTexts:
    __slots__ = ("_digests", "texts")

    def __init__(self, texts: tuple[str, ...], digests: tuple[str, ...] | None = None) -> None:
        self.texts = texts
        self._digests = digests

    @classmethod
    def of_pieces(cls, pieces: Iterable[Piece]) -> "PieceTexts":
        return cls(tuple(canonical_dumps(piece_to_data(piece)) for piece in pieces))

    @classmethod
    def of_list(cls, text: str) -> "PieceTexts":
        """Split a JSON list of piece Mementos into one canonical text per entry (no piece is decoded)."""
        return cls(tuple(map(canonical_dumps, json.loads(text))))

    @property
    def digests(self) -> tuple[str, ...]:
        if self._digests is None:
            self._digests = tuple(map(text_digest, self.texts))
        return self._digests

    def replaced(self, index: int, piece: Piece) -> "PieceTexts":
        """The same texts and digests except at `index`, which now holds `piece`."""
        text = PieceTexts.of_pieces((piece,)).texts[0]
        texts, digests = list(self.texts), list(self.digests)
        texts[index], digests[index] = text, text_digest(text)
        return PieceTexts(tuple(texts), tuple(digests))

    def joined(self) -> str:
        """The JSON list of these texts; equal to `canonical_dumps` of their parsed entries."""
        return "[" + ",".join(self.texts) + "]"
