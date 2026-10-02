"""Open a piece's outline (CAD-03): turn or shift the run between two outline points, then close the gaps.

Points inside the run move; Bézier handles take the linear part of the move. Each end of the run either
stays (the centre of a turn), merges into an existing point (a dart closing) or is copied under a new id
(a slash opening). Marks inside the moved part travel with it (`region.py`).
"""

from dataclasses import dataclass, replace

from app.domain.geom.primitives import Point2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.edges import edge_polyline
from app.domain.pattern.garment.outline_run import rebuilt, run_between
from app.domain.pattern.garment.region import carried
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_transform import transformed_segment
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Segment


@dataclass(frozen=True)
class End:
    """One end of the moved run: kept (`into` None), merged into an existing point, or copied as a new one."""

    point: PointId
    into: PointId | None = None
    merge: bool = False


@dataclass(frozen=True)
class Opening:
    first: End
    last: End
    transform: Transform2D
    before: tuple[Segment, ...] = ()  # inserted just before the run: the gap at its first end
    after: tuple[Segment, ...] = ()  # inserted just after it: the gap at its last end
    dropped: frozenset[SegmentId] = frozenset()
    apex: Point2D | None = None  # an inner centre that closes the moved part (a dart apex)


def moved_region(piece: Piece, run: tuple[Segment, ...], apex: Point2D | None) -> tuple[Point2D, ...]:
    positions = {p.id: p.position for p in piece.points}
    ring = [*(p for s in run for p in edge_polyline(s, positions)[:-1]), positions[run[-1].end]]
    return (*ring, apex) if apex is not None else tuple(ring)


def _added(piece: Piece, end: End, transform: Transform2D) -> tuple[PatternPoint, ...]:
    if end.into is None or end.merge:
        return ()
    if any(p.id == end.into for p in piece.points):
        raise ValueError(f"Point id {end.into} is already used in {piece.name}")
    return (PatternPoint(end.into, transform.apply(piece.point(end.point).position)),)


def _merged(piece: Piece, end: End) -> set[PointId]:
    if not end.merge:
        return set()
    if piece.point(end.point).grade_rule is not None:
        raise ValueError(f"Point {end.point} has a grade rule; closing the dart would remove it")
    return {end.point}


def _moved_run(run: tuple[Segment, ...], opening: Opening) -> dict[SegmentId, tuple[Segment, ...]]:
    moved = [transformed_segment(opening.transform, s, False) for s in run]
    first, last = opening.first, opening.last
    moved[0] = replace(moved[0], start=first.into or first.point)
    moved[-1] = replace(moved[-1], end=last.into or last.point)
    changes: dict[SegmentId, tuple[Segment, ...]] = {s.id: (m,) for s, m in zip(run, moved)}
    changes[run[0].id] = (*opening.before, *changes[run[0].id])
    changes[run[-1].id] = (*changes[run[-1].id], *opening.after)
    return changes


def opened(piece: Piece, opening: Opening) -> Piece:
    run = run_between(piece, opening.first.point, opening.last.point)
    move = opening.transform.apply
    marks = carried(piece, moved_region(piece, run, opening.apex), opening.transform)
    inside = {s.end for s in run[:-1]}
    gone = _merged(piece, opening.first) | _merged(piece, opening.last)
    points = tuple(
        replace(p, position=move(p.position)) if p.id in inside
        else replace(p, position=marks.points[p.id]) if p.id in marks.points
        else p
        for p in piece.points if p.id not in gone
    )
    added = (*_added(piece, opening.first, opening.transform), *_added(piece, opening.last, opening.transform))
    outline = rebuilt(piece.outline, _moved_run(run, opening), opening.dropped)
    return replace(piece, points=(*points, *added), outline=outline, internal_lines=marks.internal_lines,
                   drills=marks.drills, labels=marks.labels, grainline=marks.grainline)
