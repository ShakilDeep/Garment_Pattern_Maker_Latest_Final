"""Fold (CAD-03): keep the half of a symmetric piece from `start` forward to `end`, cut on the fold between.

The fold edge is a straight line from `end` back to `start`. The removed half must mirror the kept half
within LENGTH_CM, measured both ways between the sampled outlines; otherwise the fold is refused, never
averaged. Marks follow `fold_marks.py`; a point with a grade rule is never dropped silently. A symmetric
piece is its own mirror, so every whole cut (single or pair) becomes one cut on the fold.
"""

from dataclasses import replace
from itertools import pairwise

from app.domain.geom.lines import cross, unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label, Notch
from app.domain.pattern.cutting import CutQuantity, FoldLine
from app.domain.pattern.garment.fold_marks import FoldSides, MarkShape, require_mirrors, surviving
from app.domain.pattern.garment.opening import moved_region
from app.domain.pattern.garment.outline_run import run_between
from app.domain.pattern.garment.region import segment_distance
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.notch_position import notch_position
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_transform import reflection
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.tolerances import LENGTH_CM

LINES = MarkShape[InternalLine](lambda m: m.points, lambda m: f"internal line {m.id}")
DRILLS = MarkShape[DrillHole](lambda m: (m.position,), lambda m: f"drill hole {m.id}", lambda m: m.diameter)
LABELS = MarkShape[Label](lambda m: (m.position,), lambda m: f"label {m.id}", lambda m: m.text, paired=False)
POINTS = MarkShape[PatternPoint](lambda p: (p.position,), lambda p: f"point {p.id}")


def _gap(first: tuple[Point2D, ...], second: tuple[Point2D, ...]) -> float:
    def reach(points: tuple[Point2D, ...], line: tuple[Point2D, ...]) -> float:
        return max(min(segment_distance(p, a, b) for a, b in pairwise(line)) for p in points)

    return max(reach(first, second), reach(second, first))


def check_fold(piece: Piece, start: PointId, end: PointId, segment: SegmentId) -> None:
    if piece.fold is not None:
        raise ValueError(f"{piece.name} is already cut on the fold")
    if start == end:
        raise ValueError("the fold needs two different points")
    if any(s.id == segment for s in piece.outline):
        raise ValueError(f"Segment id {segment} is already used in {piece.name}")


def fold(piece: Piece, start: PointId, end: PointId, segment: SegmentId) -> Piece:
    check_fold(piece, start, end, segment)
    kept, removed = run_between(piece, start, end), run_between(piece, end, start)
    a, b = piece.point(start).position, piece.point(end).position
    axis = reflection(a, b)
    half = moved_region(piece, kept, None)
    gap = _gap(half, tuple(map(axis.apply, moved_region(piece, removed, None))))
    if gap > LENGTH_CM:
        raise ValueError(f"the halves differ by {gap:.2f} cm; the piece is not symmetric about {start}-{end}")
    direction = unit(Vector2D.between(a, b))
    deepest = max(half, key=lambda p: abs(cross(direction, Vector2D.between(a, p))))
    sides = FoldSides(a, direction, 1 if cross(direction, Vector2D.between(a, deepest)) > 0 else -1, axis)
    if piece.grainline is not None and sides.removed((piece.grainline.start, piece.grainline.end), "the grainline"):
        raise ValueError("the grainline lies on the removed half; move it before folding")
    return _assembled(piece, (kept, removed), sides, segment)


def _notches(piece: Piece, sides: FoldSides, gone: set[SegmentId]) -> tuple[Notch, ...]:
    shape = MarkShape[Notch](lambda n: (notch_position(piece, n),), lambda n: f"notch {n.id}")
    kept = [n for n in piece.notches if n.segment not in gone]
    require_mirrors(sides, [n for n in piece.notches if n.segment in gone], kept, shape)
    return tuple(kept)


def _assembled(piece: Piece, halves: tuple[tuple, tuple], sides: FoldSides, segment: SegmentId) -> Piece:
    kept, removed = halves
    outline_points = {i for s in piece.outline for i in (s.start, s.end)}
    on_kept = {i for s in kept for i in (s.start, s.end)}
    loose = {p.id for p in surviving(sides, [p for p in piece.points if p.id not in outline_points], POINTS)}
    points = tuple(p for p in piece.points if p.id in on_kept or p.id in loose)
    graded = [str(p.id) for p in piece.points if p not in points and p.grade_rule is not None]
    if graded:
        raise ValueError(f"point {graded[0]} has a grade rule; folding would remove it")
    return replace(
        piece, outline=(*kept, Line(segment, kept[-1].end, kept[0].start)), fold=FoldLine(segment),
        cut=CutQuantity(0, 0, piece.cut.total), points=points,
        notches=_notches(piece, sides, {s.id for s in removed}),
        internal_lines=surviving(sides, piece.internal_lines, LINES),
        drills=surviving(sides, piece.drills, DRILLS), labels=surviving(sides, piece.labels, LABELS),
    )
