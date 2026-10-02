"""Style aggregate (PM-04): any number of pieces and sizes, with a lazily decoded view per size.

Sizes are ordered labels of any text ("4", "4½", "XL"). A size in the range may have no pieces yet: grading
fills it later, and nothing here derives one size from another. Every size that has pieces has the same piece
ids in the same order, and the base size always has pieces. A piece's seam allowance (PM-03) is shared by all
sizes, because its segment and point ids are the same in every size.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from app.domain.pattern.ids import PieceId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style_checks import aligned, piece_allowances, size_labels


@dataclass(frozen=True)
class Style:
    id: StyleId
    name: str
    sizes: tuple[str, ...]
    base_size: str
    geometry: Mapping[str, SizePieces]
    allowances: Mapping[PieceId, SeamAllowance] = field(default_factory=dict)

    __hash__ = None  # type: ignore[assignment]  # the geometry mapping is not hashable

    def __post_init__(self) -> None:
        if not isinstance(self.id, StyleId):
            # ValueError, not TypeError: the API maps ValueError to 400.
            raise ValueError("A style needs a StyleId")  # noqa: TRY004
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A style needs a name")
        object.__setattr__(self, "sizes", size_labels(self.sizes))
        if self.base_size not in self.sizes:
            raise ValueError(f"The base size {self.base_size} is not in the size range")
        object.__setattr__(self, "geometry", aligned(self.sizes, self.base_size, self.geometry))
        object.__setattr__(self, "allowances", piece_allowances(self.allowances, self.piece_ids))

    @property
    def piece_ids(self) -> tuple[PieceId, ...]:
        return self.geometry[self.base_size].piece_ids

    def has_geometry(self, size: str) -> bool:
        self._require_size(size)
        return size in self.geometry

    def view(self, size: str) -> tuple[Piece, ...]:
        """The pieces of one size, decoded (and every invariant checked) on first use."""
        if not self.has_geometry(size):
            raise ValueError(f"Size {size} has no pieces yet")
        try:
            return self.geometry[size].pieces()
        except ValueError as exc:
            raise ValueError(f"Size {size}: {exc}") from exc

    def with_pieces(self, size: str, pieces: Iterable[Piece]) -> "Style":
        self._require_size(size)
        return replace(self, geometry={**self.geometry, size: SizePieces.from_pieces(pieces)})

    def with_piece(self, size: str, piece: Piece) -> "Style":
        """Replace one piece of one size (same id), keeping every other piece's cached Memento text."""
        if not self.has_geometry(size):
            raise ValueError(f"Size {size} has no pieces yet")
        return replace(self, geometry={**self.geometry, size: self.geometry[size].with_piece(piece)})

    def with_allowance(self, piece_id: PieceId, allowance: SeamAllowance) -> "Style":
        if piece_id not in self.piece_ids:
            raise KeyError(f"Unknown piece {piece_id}")
        return replace(self, allowances={**self.allowances, piece_id: allowance})

    def validate_all(self) -> None:
        """Decode every size now, e.g. before trusting an imported style document."""
        for size in self.geometry:
            self.view(size)

    def _require_size(self, size: str) -> None:
        if size not in self.sizes:
            raise KeyError(f"Unknown size {size!r}")
