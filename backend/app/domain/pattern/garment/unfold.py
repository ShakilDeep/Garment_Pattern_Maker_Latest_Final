"""Unfold (CAD-03): mirror a piece cut on the fold about its fold edge into the whole piece.

The half's outline is followed by its mirror image, run backwards. Every point (bar the fold's two ends and
construction points on the fold), notch, internal line and drill hole gets a mirrored copy whose id carries
`suffix`; a mark lying on the fold is not doubled. Labels and the grainline stay single. Mirrored points
carry no grade rule: a rule is drawn for its own side (P1-19). The fold cut becomes a single cut.
"""

from dataclasses import replace

from app.domain.pattern.annotation import Notch
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.garment.mirror import mirrored_segment, same_points
from app.domain.pattern.garment.outline_run import edge, run_between
from app.domain.pattern.ids import AnnotationId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_transform import reflection
from app.domain.pattern.point import PatternPoint
from app.domain.tolerances import COORDINATE


def unfold(piece: Piece, suffix: str) -> Piece:
    if piece.fold is None:
        raise ValueError(f"{piece.name} has no fold edge to unfold")
    fold = edge(piece, piece.fold.segment)
    on_fold = [str(n.id) for n in piece.notches if n.segment == fold.id]
    if on_fold:
        raise ValueError(f"notch {on_fold[0]} sits on the fold edge; move it before unfolding")
    axis = reflection(piece.point(fold.start).position, piece.point(fold.end).position)
    ends = {fold.start, fold.end}

    def rename(point: PointId) -> PointId:
        return point if point in ends else PointId(f"{point}{suffix}")

    def copy_id(mark_id: AnnotationId) -> AnnotationId:
        return AnnotationId(f"{mark_id}{suffix}")

    half = run_between(piece, fold.end, fold.start)
    outline = (*half, *(mirrored_segment(axis, s, rename, suffix) for s in reversed(half)))
    on_outline = {i for s in half for i in (s.start, s.end)}
    points = tuple(
        PatternPoint(rename(p.id), axis.apply(p.position)) for p in piece.points
        if p.id not in ends and (p.id in on_outline or not same_points((axis.apply(p.position),), (p.position,), COORDINATE))
    )
    notches = tuple(Notch(copy_id(n.id), SegmentId(f"{n.segment}{suffix}"), 1 - n.t) for n in piece.notches)
    lines = tuple(
        replace(m, id=copy_id(m.id), points=mirrored) for m in piece.internal_lines
        if not same_points(mirrored := tuple(map(axis.apply, m.points)), m.points, COORDINATE)
    )
    drills = tuple(
        replace(m, id=copy_id(m.id), position=axis.apply(m.position)) for m in piece.drills
        if not same_points((axis.apply(m.position),), (m.position,), COORDINATE)
    )
    cut = CutQuantity(piece.cut.single + piece.cut.on_fold, piece.cut.mirrored_pairs, 0)
    return replace(piece, points=(*piece.points, *points), outline=outline, fold=None, cut=cut,
                   notches=(*piece.notches, *notches), internal_lines=(*piece.internal_lines, *lines),
                   drills=(*piece.drills, *drills))
