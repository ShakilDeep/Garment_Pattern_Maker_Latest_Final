"""Style aggregate (PM-04): any number of pieces and sizes, with a lazily decoded view per size.

Sizes are ordered labels of any text ("4", "4½", "XL"). A size in the range may have no pieces yet: grading
fills it later, and nothing here derives one size from another. Every size that has pieces has the same piece
ids in the same order, and the base size always has pieces.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from app.domain.pattern.ids import PieceId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.size_pieces import SizePieces


def _size_labels(sizes: object) -> tuple[str, ...]:
    if not isinstance(sizes, (tuple, list)) or not all(
        isinstance(label, str) and label and label == label.strip() for label in sizes
    ):
        raise ValueError("Size labels must be a list of non-empty text without surrounding spaces")
    if not sizes:
        raise ValueError("A style needs at least one size")
    repeated = sorted(label for label, count in Counter(sizes).items() if count > 1)
    if repeated:
        raise ValueError(f"Size {', '.join(repeated)} appears more than once")
    return tuple(sizes)


def _aligned(sizes: tuple[str, ...], base: str, geometry: object) -> Mapping[str, SizePieces]:
    if not isinstance(geometry, Mapping) or not all(isinstance(v, SizePieces) for v in geometry.values()):
        raise ValueError("Style geometry must map size labels to SizePieces")
    stray = [size for size in geometry if size not in sizes]
    if stray:
        raise ValueError(f"Size {stray[0]} is not in the size range")
    if base not in geometry:
        raise ValueError(f"The base size {base} needs pieces")
    if len({stored.piece_ids for stored in geometry.values()}) > 1:
        raise ValueError("Every size must have the same pieces, in the same order")
    return MappingProxyType({size: geometry[size] for size in sizes if size in geometry})


@dataclass(frozen=True)
class Style:
    id: StyleId
    name: str
    sizes: tuple[str, ...]
    base_size: str
    geometry: Mapping[str, SizePieces]

    __hash__ = None  # type: ignore[assignment]  # the geometry mapping is not hashable

    def __post_init__(self) -> None:
        if not isinstance(self.id, StyleId):
            # ValueError, not TypeError: the API maps ValueError to 400.
            raise ValueError("A style needs a StyleId")  # noqa: TRY004
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A style needs a name")
        object.__setattr__(self, "sizes", _size_labels(self.sizes))
        if self.base_size not in self.sizes:
            raise ValueError(f"The base size {self.base_size} is not in the size range")
        object.__setattr__(self, "geometry", _aligned(self.sizes, self.base_size, self.geometry))

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

    def validate_all(self) -> None:
        """Decode every size now, e.g. before trusting an imported style document."""
        for size in self.geometry:
            self.view(size)

    def _require_size(self, size: str) -> None:
        if size not in self.sizes:
            raise KeyError(f"Unknown size {size!r}")
