"""Piece value object (PM-01).

Points not on the outline are allowed: they are construction or internal points that grading can still target.
"""
from dataclasses import dataclass, replace

from app.domain.pattern.annotation import DrillHole, InternalLine, Label, Notch
from app.domain.pattern.cutting import CutQuantity, FoldLine, Grainline
from app.domain.pattern.ids import PieceId, PointId
from app.domain.pattern.invariants import check_field_types, check_ids, check_marks, check_outline
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Segment

SEQUENCE_FIELDS = ("points", "outline", "internal_lines", "notches", "drills", "labels")


@dataclass(frozen=True)
class Piece:
    id: PieceId
    name: str
    points: tuple[PatternPoint, ...]
    outline: tuple[Segment, ...]
    cut: CutQuantity
    grainline: Grainline | None = None
    fold: FoldLine | None = None
    internal_lines: tuple[InternalLine, ...] = ()
    notches: tuple[Notch, ...] = ()
    drills: tuple[DrillHole, ...] = ()
    labels: tuple[Label, ...] = ()

    def __post_init__(self) -> None:
        for name in SEQUENCE_FIELDS:
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A piece needs a name")
        check_field_types(self)
        check_ids(self)
        check_outline(self)
        check_marks(self)

    def point(self, point_id: PointId) -> PatternPoint:
        found = next((p for p in self.points if p.id == point_id), None)
        if found is None:
            raise KeyError(str(point_id))
        return found

    def move_point(self, point_id: PointId, x: object, y: object) -> "Piece":
        moved = self.point(point_id).moved_to(x, y)
        return replace(self, points=tuple(moved if p.id == point_id else p for p in self.points))
