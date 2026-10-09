"""Format-neutral pattern interchange model (DXF-AAMA/ASTM, .RUL) — build plan M2.

Centimetres with y pointing up. A piece cut on the fold carries one half plus its mirror line; the other half
is implied. Values are copied from the source, never inferred: a mark the source lacks stays absent.
"""
from dataclasses import dataclass

Point = tuple[float, float]
Ring = tuple[Point, ...]
Segment = tuple[Point, Point]
Notch = tuple[Point, ...]  # one point: a point notch; two points: a slit from the cut line inward


@dataclass(frozen=True)
class InterchangePiece:
    name: str
    size: str
    quantity: int
    cut: Ring
    sew: tuple[Ring, ...] = ()
    mirror: Segment | None = None
    notches: tuple[Notch, ...] = ()
    grain: Segment | None = None
    category: str | None = None
    annotations: tuple[str, ...] = ()


@dataclass(frozen=True)
class InterchangeStyle:
    name: str
    sample_size: str
    pieces: tuple[InterchangePiece, ...]
    grade_rule_table: str | None = None


@dataclass(frozen=True)
class GradeRuleTable:
    """AAMA grade rules: per rule, one (dx, dy) in cm for every size, the sample size's being (0, 0)."""

    name: str
    sizes: tuple[str, ...]
    sample_size: str
    rules: tuple[tuple[Point, ...], ...]

    def __post_init__(self) -> None:
        if self.sample_size not in self.sizes:
            raise ValueError(f"Sample size {self.sample_size} is not in the size list")
        sample = self.sizes.index(self.sample_size)
        for number, deltas in enumerate(self.rules, start=1):
            if len(deltas) != len(self.sizes):
                raise ValueError(f"Rule {number} has {len(deltas)} deltas for {len(self.sizes)} sizes")
            if deltas[sample] != (0.0, 0.0):
                raise ValueError(f"Rule {number} moves the sample size")
