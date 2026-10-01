"""How a piece is laid on fabric (PM-01): grainline, fold edge and cut quantity (self, pair, fold)."""
from dataclasses import dataclass

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.point import require_point
from app.domain.tolerances import COORDINATE


@dataclass(frozen=True)
class Grainline:
    start: Point2D
    end: Point2D

    def __post_init__(self) -> None:
        require_point(self.start, "Grainline start")
        require_point(self.end, "Grainline end")
        if Vector2D.between(self.start, self.end).length <= COORDINATE:
            raise ValueError("A grainline needs two distinct points")


@dataclass(frozen=True)
class FoldLine:
    """The piece is cut on the fold along this straight outline segment (it gets no seam allowance)."""

    segment: SegmentId


@dataclass(frozen=True)
class CutQuantity:
    """Cuts per garment: as drawn, as mirrored pairs (2 pieces each) and on the fold."""

    single: int
    mirrored_pairs: int
    on_fold: int

    def __post_init__(self) -> None:
        counts = (self.single, self.mirrored_pairs, self.on_fold)
        if not all(type(count) is int and count >= 0 for count in counts) or not any(counts):
            raise ValueError("A cut quantity needs non-negative whole counts and at least one cut")

    @property
    def total(self) -> int:
        return self.single + 2 * self.mirrored_pairs + self.on_fold
