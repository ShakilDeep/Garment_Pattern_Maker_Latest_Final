"""Style invariants (PM-04): size labels, per-size geometry alignment and per-piece seam allowances."""

from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

from app.domain.pattern.ids import PieceId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.size_pieces import SizePieces


def size_labels(sizes: object) -> tuple[str, ...]:
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


def aligned(sizes: tuple[str, ...], base: str, geometry: object) -> Mapping[str, SizePieces]:
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


def piece_allowances(allowances: object, piece_ids: tuple[PieceId, ...]) -> Mapping[PieceId, SeamAllowance]:
    """Seam allowances keyed by piece id; one allowance serves every size (segment ids are stable)."""
    if not isinstance(allowances, Mapping) or not all(
        isinstance(key, PieceId) and isinstance(value, SeamAllowance) for key, value in allowances.items()
    ):
        raise ValueError("Seam allowances must map PieceIds to SeamAllowances")
    stray = sorted(str(key) for key in allowances if key not in piece_ids)
    if stray:
        raise ValueError(f"Seam allowance for unknown piece {stray[0]}")
    return MappingProxyType({key: allowances[key] for key in piece_ids if key in allowances})
