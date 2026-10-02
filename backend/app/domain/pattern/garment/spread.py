"""Parallel spreads (CAD-03): add fullness, pleats and tucks.

A straight slash joins a point on one edge to a point on another. The run of outline from the first point
forward to the second moves `amount` cm square to the slash, away from the rest of the piece, and each end
of the opening is bridged by a straight edge. A pleat or tuck takes its intake as the amount and marks both
edges of the intake with internal lines: along the whole slash for a pleat, `length` cm of it for a tuck.
"""

from dataclasses import dataclass, replace

from app.domain.geom.lines import along, unit
from app.domain.geom.primitives import Vector2D
from app.domain.geom.transform import Transform2D
from app.domain.pattern.annotation import InternalLine
from app.domain.pattern.edges import orientation
from app.domain.pattern.garment.names import Cut, SpreadNames
from app.domain.pattern.garment.opening import End, Opening, moved_region, opened
from app.domain.pattern.garment.outline_run import edge, run_between
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Line
from app.domain.pattern.split_join import split_edge


@dataclass(frozen=True)
class Spread:
    start: Cut
    end: Cut
    amount: float


def add_fullness(piece: Piece, spread: Spread, names: SpreadNames) -> Piece:
    start, end = spread.start, spread.end
    edge(piece, start.segment)
    edge(piece, end.segment)
    if start.segment == end.segment:
        raise ValueError("The slash must join two different edges")
    split = split_edge(piece, start.segment, start.t, names.q, names.e1)
    split = split_edge(split, end.segment, end.t, names.r, names.e2)
    q, r = split.point(names.q).position, split.point(names.r).position
    side = orientation(moved_region(split, run_between(split, names.q, names.r), None))
    away = unit(Vector2D(r.y - q.y, q.x - r.x))
    shift = Transform2D.translation(side * away.x * spread.amount, side * away.y * spread.amount)
    bridges = (Line(names.b1, names.q, names.qm),), (Line(names.b2, names.rm, names.r),)
    opening = Opening(End(names.q, names.qm), End(names.r, names.rm), shift, before=bridges[0], after=bridges[1])
    return opened(split, opening)


def _marked(piece: Piece, names: SpreadNames, length: float | None) -> Piece:
    position = piece.point
    q, r, qm, rm = (position(i).position for i in (names.q, names.r, names.qm, names.rm))
    if length is not None:
        slash = Vector2D.between(q, r).length
        if length >= slash:
            raise ValueError(f"the tuck length {length:g} cm must be shorter than the slash ({slash:.2f} cm)")
        direction = unit(Vector2D.between(q, r))
        r, rm = along(q, direction, length), along(qm, direction, length)
    lines = (InternalLine(names.fixed, (q, r)), InternalLine(names.moved, (qm, rm)))
    return replace(piece, internal_lines=(*piece.internal_lines, *lines))


def pleat(piece: Piece, spread: Spread, names: SpreadNames) -> Piece:
    return _marked(add_fullness(piece, spread, names), names, None)


def tuck(piece: Piece, spread: Spread, length: float, names: SpreadNames) -> Piece:
    return _marked(add_fullness(piece, spread, names), names, length)
