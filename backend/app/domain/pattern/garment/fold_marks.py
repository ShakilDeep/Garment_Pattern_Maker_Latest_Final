"""Which marks survive a fold (CAD-03): those on the kept half or on the fold line stay.

A piece cut on the fold is marked through both layers, so every mark off the fold must already have its
mirror image on the other half (within LENGTH_CM): a removed-half mark with no twin would be lost, and a
kept-half mark with no twin would be doubled. Either way the fold is refused by name. Labels and the
grainline are not doubled by unfold, so a kept label needs no twin. A mark across the fold line is refused.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.domain.geom.lines import cross
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.garment.mirror import same_points
from app.domain.tolerances import COORDINATE, LENGTH_CM


@dataclass(frozen=True)
class FoldSides:
    start: Point2D
    direction: Vector2D
    kept: int  # the sign of `cross(direction, p - start)` on the kept half
    axis: Transform2D

    def side(self, point: Point2D) -> int:
        offset = cross(self.direction, Vector2D.between(self.start, point))
        return 0 if abs(offset) <= COORDINATE else (1 if offset > 0 else -1)

    def removed(self, points: Sequence[Point2D], what: str) -> bool:
        sides = {self.side(p) for p in points} - {0}
        if len(sides) > 1:
            raise ValueError(f"{what} crosses the fold line; move or split it before folding")
        return sides == {-self.kept}

    def mirrored(self, points: Sequence[Point2D]) -> tuple[Point2D, ...]:
        return tuple(self.axis.apply(p) for p in points)


@dataclass(frozen=True)
class MarkShape[Mark]:
    """How to read one kind of mark: its points, its name in messages, what a twin must share, and whether
    a kept mark needs a twin too (False for labels, which unfold keeps single)."""

    points: Callable[[Mark], tuple[Point2D, ...]]
    name: Callable[[Mark], str]
    key: Callable[[Mark], object] = lambda _mark: None
    paired: bool = True


def _has_twin[Mark](sides: FoldSides, mark: Mark, others: Sequence[Mark], shape: MarkShape[Mark]) -> bool:
    image = sides.mirrored(shape.points(mark))
    return any(
        same_points(image, shape.points(o), LENGTH_CM) or same_points(image[::-1], shape.points(o), LENGTH_CM)
        for o in others if shape.key(o) == shape.key(mark)
    )


def require_mirrors[Mark](
    sides: FoldSides, removed: Sequence[Mark], kept: Sequence[Mark], shape: MarkShape[Mark]
) -> None:
    for mark in removed:
        if not _has_twin(sides, mark, kept, shape):
            raise ValueError(f"{shape.name(mark)} on the removed half has no mirror on the kept half; add one first")
    for mark in kept if shape.paired else ():
        on_fold = all(sides.side(p) == 0 for p in shape.points(mark))
        if not on_fold and not _has_twin(sides, mark, removed, shape):
            raise ValueError(
                f"{shape.name(mark)} on the kept half has no mirror on the removed half; "
                "folding would mark it on both layers"
            )


def surviving[Mark](sides: FoldSides, marks: Sequence[Mark], shape: MarkShape[Mark]) -> tuple[Mark, ...]:
    removed = [m for m in marks if sides.removed(shape.points(m), shape.name(m))]
    kept = [m for m in marks if m not in removed]
    require_mirrors(sides, removed, kept, shape)
    return tuple(kept)
