"""Declarative piece recipes for the 1078375 block (docs/drafting/shirt.md), read by ``draft.draft_recipe``.

A point is a linear formula of named measurements per axis, in the piece's own frame; the rest of its PDS
position is a shape offset kept with the data (``shape.py``). Points are listed counter-clockwise and each
edge runs from a point to the next, so ``kinds`` and ``roles`` are indexed like ``points``.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Linear = Mapping[str, float]  # measurement name -> coefficient; {} is 0
EdgeKind = Literal["line", "cubic"]


@dataclass(frozen=True)
class PointRecipe:
    name: str
    x: Linear
    y: Linear


@dataclass(frozen=True)
class NotchRecipe:
    name: str
    start: str
    end: str


@dataclass(frozen=True)
class PieceRecipe:
    id: str
    name: str
    cut: tuple[int, int, int]  # single, mirrored pairs, on fold
    origin: tuple[str, str]  # the frame's x comes from the first point's PDS x, y from the second's PDS y
    points: tuple[PointRecipe, ...]
    kinds: tuple[EdgeKind, ...]
    roles: tuple[str, ...]  # finishing role of each edge; "fold" for the fold edge
    notches: tuple[NotchRecipe, ...] = ()
    smooth: tuple[str, ...] = ()  # points where the PDS line runs on as one curve (tangent-continuous)

    def __post_init__(self) -> None:
        if not len(self.points) == len(self.kinds) == len(self.roles):
            raise ValueError(f"Recipe {self.id} needs one edge kind and role per point")

    def edges(self) -> tuple[tuple[str, str], ...]:
        names = [point.name for point in self.points]
        return tuple(zip(names, names[1:] + names[:1], strict=True))

    @property
    def fold(self) -> tuple[str, str] | None:
        return next((edge for edge, role in zip(self.edges(), self.roles, strict=True) if role == "fold"), None)


def at(name: str, x: Linear, y: Linear) -> PointRecipe:
    return PointRecipe(name, x, y)


def evaluate(formula: Linear, measures: Mapping[str, float]) -> float:
    missing = sorted(name for name in formula if name not in measures)
    if missing:
        raise ValueError(f"A point formula needs measurements {', '.join(missing)}")
    return sum(coefficient * measures[name] for name, coefficient in formula.items())
