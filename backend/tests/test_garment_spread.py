"""P1-10 (CAD-03): slash-and-spread pivots one side about a hinge; add fullness spreads it parallel."""

from dataclasses import replace
from math import radians, sin

import pytest
from garment_fixture import bodice_style, distance, piece_of, position, run, seam_length
from test_cad_guard import GUARD
from test_cad_style_bus import BUS

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import InternalLine
from app.domain.pattern.ids import AnnotationId
from app.domain.pattern.piece_transform import rotation_about

HINGED = {"hinge_id": "c", "segment_id": "s1", "t": 0.5, "angle_degrees": 10, "slash_id": "k"}
FULL = {"from_segment": "s1", "from_t": 0.5, "to_segment": "s3", "to_t": 0.5, "amount": 6, "slash_id": "f"}


def test_slash_and_spread_opens_the_slash_by_the_angle_about_the_hinge():
    style = run(BUS, bodice_style(), "slash_spread", **HINGED)
    piece = piece_of(style)
    radius = distance(Point2D(20, 0), Point2D(40, 50))
    assert distance(position(piece, "k.qm"), position(piece, "k.q")) == pytest.approx(2 * radius * sin(radians(5)))
    assert position(piece, "k.qm").x < 20 and position(piece, "c") == Point2D(40, 50)
    turn = rotation_about(Point2D(40, 50), -10)
    for moved, original in ((piece.grainline.start, (5, 10)), (piece.labels[0].position, (8, 30))):
        expected = turn.apply(Point2D(*original))
        assert (moved.x, moved.y) == pytest.approx((expected.x, expected.y), abs=1e-6)
    GUARD.check(bodice_style(), style)


def test_add_fullness_moves_one_side_parallel_and_bridges_both_ends():
    before = bodice_style()
    after = run(BUS, before, "add_fullness", **FULL)
    piece = piece_of(after)
    assert position(piece, "b") == Point2D(46, 0) and position(piece, "c") == Point2D(46, 50)
    assert distance(position(piece, "f.q"), position(piece, "f.qm")) == pytest.approx(6)
    assert distance(position(piece, "f.r"), position(piece, "f.rm")) == pytest.approx(6)
    assert seam_length(piece) == pytest.approx(seam_length(piece_of(before)) + 12, abs=0.01)
    assert piece.grainline == piece_of(before).grainline and piece.notches == piece_of(before).notches
    GUARD.check(before, after)


def _crossed():
    """An internal line from the left half into the right half, across both slashes."""
    style = bodice_style()
    piece = piece_of(style)
    line = InternalLine(AnnotationId("hip"), (Point2D(5, 20), Point2D(35, 20)))
    return style.with_piece("M", replace(piece, internal_lines=(line,)))


@pytest.mark.parametrize(("command", "params"), [("slash_spread", HINGED), ("add_fullness", FULL)])
def test_a_mark_across_the_slash_is_refused_by_name(command, params):
    with pytest.raises(ValueError, match="Size M: internal line hip crosses the slash"):
        run(BUS, _crossed(), command, **params)


@pytest.mark.parametrize(
    ("command", "change", "match"),
    [
        ("slash_spread", {"angle_degrees": 0}, "angle_degrees must be more than 0"),
        ("slash_spread", {"hinge_id": "a"}, "hinge a is an end of the slashed edge s1"),
        ("slash_spread", {"hinge_id": "k.zz"}, "k.zz"),
        ("add_fullness", {"to_segment": "s1", "to_t": 0.8}, "two different edges"),
        ("add_fullness", {"amount": -1}, "amount must be a positive"),
    ],
)
def test_bad_spreads_are_refused(command, change, match):
    params = {**(HINGED if command == "slash_spread" else FULL), **change}
    with pytest.raises((ValueError, KeyError), match=match):
        run(BUS, bodice_style(), command, **params)
