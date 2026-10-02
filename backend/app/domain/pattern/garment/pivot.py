"""Pivot tools (CAD-03): rotate or close a dart, and slash-and-spread about a hinge.

Each cuts an edge at `cut` and turns the run of outline from the pivot side forward to the cut. Rotating
a dart turns the run after it about the apex until its legs meet, and opens the same angle at the cut as a
new dart: a rigid turn and an exact split, so every seam keeps its length. Closing a dart bridges the
opening with a straight edge instead; slash-and-spread turns the run about a hinge on the outline, the way
that opens the slash.
"""

from dataclasses import dataclass, replace
from math import atan2, degrees

from app.domain.pattern.edges import orientation
from app.domain.pattern.garment.dart import clear_of_marks, dart_at, true_legs
from app.domain.pattern.garment.names import Cut, DartNames, SlashNames
from app.domain.pattern.garment.opening import End, Opening, moved_region, opened
from app.domain.pattern.garment.outline_run import edge, run_between
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.piece_transform import rotation_about
from app.domain.pattern.segment import Line
from app.domain.pattern.split_join import split_edge


@dataclass(frozen=True)
class Hinge:
    point: PointId
    angle_degrees: float


def _dart_opening(piece: Piece, apex: PointId, cut: Cut, split_as: tuple[PointId, SegmentId]) -> tuple[Piece, Opening]:
    """The piece cut at `cut`, and the turn that closes the dart at `apex` (its last end still to be set)."""
    dart = dart_at(piece, apex)
    true_legs(piece, dart)
    clear_of_marks(piece, dart, cut.segment)
    centre = piece.point(apex).position
    l1, l2 = piece.point(dart.leg1.start).position, piece.point(dart.leg2.end).position
    angle = atan2(l1.y - centre.y, l1.x - centre.x) - atan2(l2.y - centre.y, l2.x - centre.x)
    split = split_edge(piece, cut.segment, cut.t, *split_as)
    start = End(dart.leg2.end, dart.leg1.start, merge=True)
    turn = rotation_about(centre, degrees(angle))
    return split, Opening(start, End(split_as[0]), turn, dropped=frozenset({dart.leg1.id, dart.leg2.id}), apex=centre)


def rotate_dart(piece: Piece, apex: PointId, cut: Cut, names: DartNames) -> Piece:
    split, opening = _dart_opening(piece, apex, cut, (names.l2, names.edge))
    legs = (Line(names.leg1, names.l1, apex), Line(names.leg2, apex, names.l2))
    return opened(split, replace(opening, last=End(names.l2, names.l1), after=legs))


def close_dart(piece: Piece, apex: PointId, cut: Cut, names: SlashNames) -> Piece:
    split, opening = _dart_opening(piece, apex, cut, (names.q, names.edge))
    bridge = (Line(names.bridge, names.qm, names.q),)
    return opened(split, replace(opening, last=End(names.q, names.qm), after=bridge))


def slash_spread(piece: Piece, hinge: Hinge, cut: Cut, names: SlashNames) -> Piece:
    slashed = edge(piece, cut.segment)
    piece.point(hinge.point)
    if hinge.point in (slashed.start, slashed.end):
        raise ValueError(f"The hinge {hinge.point} is an end of the slashed edge {cut.segment}; pick another point")
    split = split_edge(piece, cut.segment, cut.t, names.q, names.edge)
    region = moved_region(split, run_between(split, hinge.point, names.q), None)
    try:
        side = orientation(region)
    except ValueError as exc:
        raise ValueError(f"the hinge {hinge.point} and the slash are in line; pick another hinge") from exc
    turn = rotation_about(split.point(hinge.point).position, -side * hinge.angle_degrees)
    bridge = (Line(names.bridge, names.qm, names.q),)
    return opened(split, Opening(End(hinge.point), End(names.q, names.qm), turn, after=bridge))
