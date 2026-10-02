"""P1-10 (CAD-03) acceptance: dart rotation keeps seam length within 0.01 cm; create and close darts."""


import pytest
from garment_fixture import bodice_style, distance, piece_of, position, run, seam_length
from test_cad_guard import GUARD
from test_cad_style_bus import BUS

from app.application.cad.history import History
from app.application.errors import GeometryInvalid
from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import PointId

OLD_LEGS, NEW_LEGS = ("d1.leg1", "d1.leg2"), ("d2.leg1", "d2.leg2")


def _darted():
    return run(BUS, bodice_style(), "create_dart", segment_id="s1", t_start=0.4, t_end=0.5, length=15, dart_id="d1")


def test_create_dart_cuts_a_v_into_the_edge_with_its_apex_inside():
    piece = piece_of(_darted())
    assert [str(s.id) for s in piece.outline][:4] == ["s1", "d1.leg1", "d1.leg2", "d1.edge"]
    assert position(piece, "d1.l1") == Point2D(16, 0) and position(piece, "d1.l2") == Point2D(20, 0)
    assert position(piece, "d1.apex") == Point2D(18, 15)
    assert position(piece_of(_darted(), "S"), "d1.apex") == Point2D(16.2, 15)
    GUARD.check(bodice_style(), _darted())


@pytest.mark.parametrize(("segment", "t"), [("s2", 0.6), ("s3", 0.5)])
def test_rotating_a_dart_keeps_every_seam_length_within_a_hundredth_of_a_cm(segment, t):
    before = _darted()
    after = run(BUS, before, "rotate_dart", apex_id="d1.apex", segment_id=segment, t=t, dart_id="d2")
    for size in ("S", "M"):
        old, new = piece_of(before, size), piece_of(after, size)
        assert seam_length(new, NEW_LEGS) == pytest.approx(seam_length(old, OLD_LEGS), abs=0.01)
        assert {"d1.leg1", "d1.leg2"}.isdisjoint(str(s.id) for s in new.outline)
        assert PointId("d1.l2") not in {p.id for p in new.points}
        apex = position(new, "d1.apex")
        assert distance(position(new, "d2.l1"), apex) == pytest.approx(distance(position(new, "d2.l2"), apex), abs=1e-6)
    GUARD.check(before, after)


def test_the_rotated_dart_opens_where_the_slash_meets_the_edge():
    piece = piece_of(run(BUS, _darted(), "rotate_dart", apex_id="d1.apex", segment_id="s2", t=0.6, dart_id="d2"))
    assert position(piece, "d2.l2") == Point2D(40, 30)
    assert position(piece, "b") != Point2D(40, 0) and position(piece, "d1.l1") == Point2D(16, 0)
    order = [str(s.id) for s in piece.outline]
    assert order[order.index("s2") + 1:order.index("s2") + 4] == ["d2.leg1", "d2.leg2", "d2.edge"]


def test_closing_a_dart_turns_its_intake_into_a_bridged_opening():
    closed = piece_of(run(BUS, _darted(), "close_dart", apex_id="d1.apex", segment_id="s2", t=0.6, slash_id="k"))
    bridge = next(s for s in closed.outline if str(s.id) == "k.bridge")
    assert (str(bridge.start), str(bridge.end)) == ("k.qm", "k.q")
    assert distance(position(closed, "k.qm"), position(closed, "k.q")) > 1
    assert PointId("d1.apex") in {p.id for p in closed.points}
    assert PointId("d1.apex") not in {s.start for s in closed.outline}


@pytest.mark.parametrize(
    ("params", "error", "match"),
    [
        ({"segment_id": "d1.leg1", "t": 0.5}, ValueError, "dart leg"),
        ({"segment_id": "s2", "t": 1.0}, ValueError, "strictly between 0 and 1"),
        ({"apex_id": "zz", "segment_id": "s2", "t": 0.5}, KeyError, "zz"),
        ({"apex_id": "d1.l1", "segment_id": "s2", "t": 0.5}, ValueError, "not a dart apex"),
    ],
)
def test_bad_dart_rotations_are_refused(params, error, match):
    with pytest.raises(error, match=match):
        run(BUS, _darted(), "rotate_dart", **{"apex_id": "d1.apex", "dart_id": "d2", **params})


def test_unequal_legs_are_refused_naming_the_size():
    moved = {"size": "M", "piece_id": "bodice", "point_id": "d1.l2", "x": 21, "y": 0}
    uneven = BUS.dispatch(_darted(), History(), "move_point", moved)[0]
    with pytest.raises(ValueError, match="Size M: dart legs differ by 0.164 cm"):
        run(BUS, uneven, "rotate_dart", apex_id="d1.apex", segment_id="s2", t=0.6, dart_id="d2")


def test_a_dart_whose_apex_falls_outside_the_piece_is_blocked():
    deep = run(BUS, bodice_style(), "create_dart", segment_id="s1", t_start=0.4, t_end=0.5, length=80, dart_id="d1")
    with pytest.raises(GeometryInvalid):
        GUARD.check(bodice_style(), deep)


@pytest.mark.parametrize(
    ("change", "match"),
    [({"t_start": 0.5, "t_end": 0.4}, "t_start must be before t_end"), ({"length": 0}, "length must be a positive")],
)
def test_bad_dart_shapes_are_refused(change, match):
    params = {"segment_id": "s1", "t_start": 0.4, "t_end": 0.5, "length": 15, "dart_id": "d1", **change}
    with pytest.raises(ValueError, match=match):
        run(BUS, bodice_style(), "create_dart", **params)
