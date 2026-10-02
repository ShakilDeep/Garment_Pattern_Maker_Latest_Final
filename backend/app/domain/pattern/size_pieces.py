"""One size's pieces in a Style (PM-04), decoded only when first viewed.

A size loaded from JSON keeps its pieces as JSON text, so a 200-piece x 30-size style loads without building
6,000 pieces (about 5 s). Loading checks only the piece ids; every piece invariant runs when the size is first
viewed (`Style.view`, `Style.validate_all`), and the text is then replaced by the pieces' canonical Memento
(unknown keys dropped, numbers quantized). Equality means "same Memento text", so a never-viewed size compares
by its text as loaded. Per-piece texts and digests are cached for the command history; `with_piece` keeps them
for every piece it does not replace. Caches are not locked: two threads may both fill one, with equal values.
"""

import json
from collections.abc import Iterable

from app.domain.pattern.canonical import canonical_dumps
from app.domain.pattern.ids import PieceId, require_unique
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_texts import PieceTexts
from app.domain.pattern.serialize import piece_from_data


class SizePieces:
    __slots__ = ("_chunks", "_piece_ids", "_pieces", "_text")

    def __init__(self, pieces: tuple[Piece, ...] | None, text: str | None, piece_ids: tuple[PieceId, ...]):
        """Use `from_pieces`, `from_entries` or `from_piece_texts`."""
        if (pieces is None) == (text is None):
            raise ValueError("SizePieces needs either pieces or their JSON text")
        if pieces is not None and piece_ids != tuple(piece.id for piece in pieces):
            raise ValueError("SizePieces ids must be the ids of its pieces")
        require_unique(piece_ids, "piece")
        self._piece_ids, self._pieces, self._text = piece_ids, pieces, text
        self._chunks: PieceTexts | None = None

    @classmethod
    def from_pieces(cls, pieces: Iterable[Piece]) -> "SizePieces":
        built = tuple(pieces)
        if not all(isinstance(piece, Piece) for piece in built):
            raise ValueError("A size's pieces must be Piece objects")
        return cls(built, None, tuple(piece.id for piece in built))

    @classmethod
    def from_entries(cls, entries: object) -> "SizePieces":
        """Memento entries (`piece_to_data` objects), checked for their ids only until viewed."""
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            raise ValueError("A size's pieces must be a list of piece objects")
        if not all("id" in entry for entry in entries):
            raise ValueError("Invalid style data: missing field 'id'")
        try:
            text = canonical_dumps(entries)
        except ValueError as exc:
            raise ValueError("Invalid style data: a number is out of range") from exc
        return cls(None, text, tuple(PieceId(entry["id"]) for entry in entries))

    @classmethod
    def from_piece_texts(cls, chunks: PieceTexts) -> "SizePieces":
        """Rebuild from `piece_texts()` (the command history's per-piece chunks)."""
        size = cls.from_entries(json.loads(chunks.joined()))
        size._chunks, size._text = chunks, chunks.joined()  # text and chunks agree even if not canonical
        return size

    @property
    def piece_ids(self) -> tuple[PieceId, ...]:
        return self._piece_ids

    def pieces(self) -> tuple[Piece, ...]:
        if self._pieces is None:
            decoded = tuple(piece_from_data(entry) for entry in json.loads(self.text()))
            self._chunks, self._text = PieceTexts.of_pieces(decoded), None
            self._pieces = decoded
        return self._pieces

    def with_piece(self, piece: Piece) -> "SizePieces":
        """A copy with the piece of the same id replaced; every other piece keeps its cached text and digest."""
        if piece.id not in self._piece_ids:
            raise KeyError(f"Unknown piece {piece.id}")
        index = self._piece_ids.index(piece.id)
        pieces = list(self.pieces())
        pieces[index] = piece
        replaced = SizePieces(tuple(pieces), None, self._piece_ids)
        replaced._chunks = self.piece_texts().replaced(index, piece)
        return replaced

    def piece_texts(self) -> PieceTexts:
        """Each piece's Memento as canonical JSON text, in order (the list `text()` joins)."""
        if self._chunks is None:
            pieces = self._pieces
            self._chunks = PieceTexts.of_pieces(pieces) if pieces is not None else PieceTexts.of_list(self.text())
        return self._chunks

    def text(self) -> str:
        """This size's piece Mementos as a JSON list (canonical once built from, or decoded to, pieces)."""
        if self._text is None:
            self._text = self.piece_texts().joined()
        return self._text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SizePieces) and self.text() == other.text()

    __hash__ = None  # type: ignore[assignment]
