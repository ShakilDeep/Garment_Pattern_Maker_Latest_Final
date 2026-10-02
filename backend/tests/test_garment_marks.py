"""P1-10: marks inside the turned part of a piece travel with it; marks outside stay; undo restores hashes."""

from dataclasses import replace
from math import atan2, degrees

import pytest
from garment_fixture import bodice_style, piece_of, run
from test_cad_style_bus import BUS

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label
from app.domain.pattern.cutting import Grainline
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.ids import AnnotationId, PointId
from app.domain.pattern.piece_transform import rotation_about
from app.domain.pattern.point import PatternPoint

APEX, L1, L2 = Point2D(18, 15), Point2D(16, 0), Point2D(20, 0)
DART = {"segment_id": "s1", "t_start": 0.4, "t_end": 0.5, "length": 15, "dart_id": "d1"}
ROTATE = {"apex_id": "d1.apex", "segment_id": "s2", "t": 0.6, "dart_id": "d2"}


def _marked(**changes):
    style = run(BUS, bodice_style(), "create_dart", **DART)
    piece = piece_of(style)
    drills = (DrillHole(AnnotationId("in"), Point2D(30, 8), 0.4), DrillHole(AnnotationId("out"), Point2D(5, 45), 0.4))
    labels = (*piece.labels, Label(AnnotationId("side"), "Side", Point2D(34, 12), 10))
    points = (*piece.points, PatternPoint(PointId("x"), Point2D(32, 5)))
    return style.with_piece("M", replace(piece, drills=drills, labels=labels, points=points, **changes))


def _turn():
    angle = atan2(L1.y - APEX.y, L1.x - APEX.x) - atan2(L2.y - APEX.y, L2.x - APEX.x)
    return rotation_about(APEX, degrees(angle)), degrees(angle)


def _close(point, expected):
    return (point.x, point.y) == pytest.approx((expected.x, expected.y), abs=1e-6)


def test_marks_inside_the_turned_part_turn_with_it_and_the_rest_stay():
    piece = piece_of(run(BUS, _marked(), "rotate_dart", **ROTATE))
    turn, angle = _turn()
    inside, outside = piece.drills
    assert _close(inside.position, turn.apply(Point2D(30, 8))) and outside.position == Point2D(5, 45)
    side = piece.labels[1]
    assert _close(side.position, turn.apply(Point2D(34, 12))) and side.rotation_degrees == pytest.approx(10 + angle)
    assert piece.labels[0].position == Point2D(8, 30) and piece.grainline == Grainline(Point2D(5, 10), Point2D(5, 40))
    assert _close(piece.point(PointId("x")).position, turn.apply(Point2D(32, 5)))


def test_a_grainline_across_the_slash_is_refused():
    crossing = _marked(grainline=Grainline(Point2D(10, 20), Point2D(38, 20)))
    with pytest.raises(ValueError, match="Size M: the grainline crosses the slash"):
        run(BUS, crossing, "rotate_dart", **ROTATE)


def test_undo_after_a_dart_rotation_restores_identical_hashes():
    style = _marked()
    rotated, history = BUS.dispatch(style, History(), "rotate_dart", {"piece_id": "bodice", **ROTATE})
    restored, _ = BUS.undo(rotated, history)
    for size in ("S", "M"):
        assert geometry_hash(piece_of(restored, size)) == geometry_hash(piece_of(style, size))


def test_a_line_running_through_a_new_dart_is_refused():
    style = bodice_style()
    hip = InternalLine(AnnotationId("hip"), (Point2D(5, 5), Point2D(35, 5)))
    lined = style.with_piece("M", replace(piece_of(style), internal_lines=(hip,)))
    with pytest.raises(ValueError, match="Size M: internal line hip crosses the dart at d1.apex"):
        run(BUS, lined, "create_dart", **DART)
