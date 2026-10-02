"""Darts (CAD-03): a V cut into the outline, leg end l1 -> apex -> leg end l2, with straight legs.

A new dart's leg ends sit on the edge at the given parameters; its apex lies `length` cm into the piece,
square to the chord between them from its midpoint. An existing dart is recognised by its apex: two
straight legs meeting where the outline turns back into the piece.
"""

from dataclasses import dataclass, replace

from app.domain.geom.lines import cross, unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.edges import orientation, stitch_ring
from app.domain.pattern.garment.dart_marks import refuse_in_dart
from app.domain.pattern.garment.names import DartNames
from app.domain.pattern.garment.outline_run import edge, leaving, rebuilt
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.pattern.split_join import split_edge
from app.domain.tolerances import LENGTH_CM

# Closing a dart merges one leg end into the other; legs equal to 0.001 cm move that edge end by at most a
# tenth of the 0.01 cm seam-length budget (CAD-03).
DART_LEGS_CM = LENGTH_CM / 10


@dataclass(frozen=True)
class DartSpan:
    segment: SegmentId
    t_start: float
    t_end: float
    length: float


@dataclass(frozen=True)
class Dart:
    leg1: Line
    leg2: Line

    @property
    def apex(self) -> PointId:
        return self.leg1.end


def create_dart(piece: Piece, span: DartSpan, names: DartNames) -> Piece:
    if not span.t_start < span.t_end:
        raise ValueError("t_start must be before t_end")
    side = orientation(stitch_ring(piece))
    opened = split_edge(piece, span.segment, span.t_end, names.l2, names.edge)
    opened = split_edge(opened, span.segment, span.t_start / span.t_end, names.l1, names.leg1)
    inside = [str(n.id) for n in opened.notches if n.segment == names.leg1]
    if inside:
        raise ValueError(f"Notch {inside[0]} falls inside the dart opening; move it first")
    l1, l2 = opened.point(names.l1).position, opened.point(names.l2).position
    chord = unit(Vector2D.between(l1, l2))
    middle = Point2D((l1.x + l2.x) / 2, (l1.y + l2.y) / 2)
    apex = Point2D(middle.x - side * chord.y * span.length, middle.y + side * chord.x * span.length)
    legs = (Line(names.leg1, names.l1, names.apex), Line(names.leg2, names.apex, names.l2))
    darted = replace(opened, points=(*opened.points, PatternPoint(names.apex, apex)),
                     outline=rebuilt(opened.outline, {names.leg1: legs}, ()))
    refuse_in_dart(darted, (l1, apex, l2), f"the dart at {names.apex}")
    return darted


def dart_at(piece: Piece, apex: PointId) -> Dart:
    leg2 = piece.outline[leaving(piece, apex)]
    leg1 = next(s for s in piece.outline if s.end == apex)
    positions = {p.id: p.position for p in piece.points}
    if isinstance(leg1, Line) and isinstance(leg2, Line):
        before = Vector2D.between(positions[leg1.start], positions[apex])
        after = Vector2D.between(positions[apex], positions[leg2.end])
        if cross(before, after) * orientation(stitch_ring(piece)) < 0:
            return Dart(leg1, leg2)
    raise ValueError(f"Point {apex} is not a dart apex: two straight legs must turn back into the piece there")


def true_legs(piece: Piece, dart: Dart) -> None:
    ends = [(piece.point(leg.start).position, piece.point(leg.end).position) for leg in (dart.leg1, dart.leg2)]
    lengths = [Vector2D.between(*pair).length for pair in ends]
    if abs(lengths[0] - lengths[1]) > DART_LEGS_CM:
        raise ValueError(f"dart legs differ by {abs(lengths[0] - lengths[1]):.3f} cm; true the dart first")


def clear_of_marks(piece: Piece, dart: Dart, slashed: SegmentId) -> None:
    """The slash is not a leg, no notch sits on a leg, and no mark lies inside the V."""
    edge(piece, slashed)
    legs = (dart.leg1.id, dart.leg2.id)
    if slashed in legs:
        raise ValueError(f"Edge {slashed} is a dart leg; slash another edge")
    on_leg = [str(n.id) for n in piece.notches if n.segment in legs]
    if on_leg:
        raise ValueError(f"notch {on_leg[0]} sits on a leg of the dart at {dart.apex}; move it first")
    corners = (piece.point(dart.leg1.start).position, piece.point(dart.apex).position,
               piece.point(dart.leg2.end).position)
    refuse_in_dart(piece, corners, f"the dart at {dart.apex}")
