"""P1-10 (CAD-03): a pleat or tuck adds its intake as a parallel spread and marks both edges of the intake."""


import pytest
from garment_fixture import bodice_style, distance, piece_of, position, run
from test_cad_guard import GUARD
from test_cad_style_bus import BUS

from app.domain.geom.primitives import Point2D

PLEAT = {"from_segment": "s1", "from_t": 0.5, "to_segment": "s3", "to_t": 0.5, "intake": 8, "slash_id": "p"}


def _lines(piece):
    return {str(line.id): line.points for line in piece.internal_lines}


def test_a_pleat_spreads_by_its_intake_and_marks_the_full_slash_on_both_sides():
    after = run(BUS, bodice_style(), "pleat", **PLEAT)
    piece = piece_of(after)
    lines = _lines(piece)
    assert lines["p.fixed"] == (position(piece, "p.q"), position(piece, "p.r"))
    assert lines["p.moved"] == (position(piece, "p.qm"), position(piece, "p.rm"))
    assert position(piece, "b") == Point2D(48, 0)
    GUARD.check(bodice_style(), after)


def test_a_tuck_marks_only_its_stitched_length_from_the_first_edge():
    piece = piece_of(run(BUS, bodice_style(), "tuck", **PLEAT, length=12))
    fixed, moved = _lines(piece)["p.fixed"], _lines(piece)["p.moved"]
    assert fixed[0] == position(piece, "p.q") and distance(*fixed) == pytest.approx(12)
    assert moved[0] == position(piece, "p.qm") and distance(*moved) == pytest.approx(12)
    assert fixed[1] == Point2D(20, 12)


def test_the_same_tuck_in_the_small_size_scales_its_slash_not_its_length():
    style = run(BUS, bodice_style(), "tuck", **PLEAT, length=12)
    fixed = _lines(piece_of(style, "S"))["p.fixed"]
    assert fixed[0] == Point2D(18, 0) and distance(*fixed) == pytest.approx(12)


@pytest.mark.parametrize(
    ("command", "change", "match"),
    [
        ("tuck", {"length": 80}, "Size S: the tuck length 80 cm must be shorter than the slash"),
        ("tuck", {"length": 0}, "length must be a positive"),
        ("pleat", {"intake": 0}, "intake must be a positive"),
        ("pleat", {"slash_id": "bad id"}, "Invalid identifier"),
    ],
)
def test_bad_pleats_and_tucks_are_refused(command, change, match):
    params = {**PLEAT, **({"length": 12} if command == "tuck" else {}), **change}
    with pytest.raises(ValueError, match=match):
        run(BUS, bodice_style(), command, **params)
