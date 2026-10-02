"""P1-10: the per-piece seam allowance follows every garment edit, so the cut outline stays valid and true."""

from garment_fixture import bodice_style, run
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style

from app.application.cad.history import History
from app.domain.pattern.ids import PieceId, PointId, SegmentId


def _allowed(style, piece, edges, corners=None):
    params = {"piece_id": piece, "default_width": 1, "edge_widths": edges, "corner_styles": corners or {}}
    return BUS.dispatch(style, History(), "set_seam_allowance", params)[0]


def _widths(style, piece="bodice"):
    return {str(key): width for key, width in style.allowances[PieceId(piece)].edge_widths}


DART = {"segment_id": "s1", "t_start": 0.4, "t_end": 0.5, "length": 15, "dart_id": "d1"}


def test_a_new_dart_keeps_the_hem_width_on_both_sides_and_stays_cuttable():
    before = _allowed(bodice_style(), "bodice", {"s1": 2.5})
    after = run(BUS, before, "create_dart", **DART)
    assert _widths(after) == {"s1": 2.5, "d1.edge": 2.5}
    GUARD.check(before, after)


def test_rotating_a_dart_moves_its_leg_widths_to_the_new_legs():
    darted = _allowed(run(BUS, bodice_style(), "create_dart", **DART), "bodice",
                      {"s2": 1.5, "d1.leg1": 0.5, "d1.leg2": 0.5}, {"d1.l2": "square"})
    after = run(BUS, darted, "rotate_dart", apex_id="d1.apex", segment_id="s2", t=0.6, dart_id="d2")
    assert _widths(after) == {"s2": 1.5, "d2.edge": 1.5, "d2.leg1": 0.5, "d2.leg2": 0.5}
    assert after.allowances[PieceId("bodice")].corner_styles == ()
    GUARD.check(darted, after)


def test_closing_a_dart_gives_the_bridge_the_slashed_edge_width():
    darted = _allowed(run(BUS, bodice_style(), "create_dart", **DART), "bodice", {"s2": 1.5, "d1.leg1": 0})
    after = run(BUS, darted, "close_dart", apex_id="d1.apex", segment_id="s2", t=0.6, slash_id="k")
    assert _widths(after) == {"s2": 1.5, "k.edge": 1.5, "k.bridge": 1.5}
    GUARD.check(darted, after)


def test_add_fullness_bridges_take_the_width_of_the_edge_they_bridge():
    before = _allowed(bodice_style(), "bodice", {"s1": 2.5, "s3": 1.2})
    params = {"from_segment": "s1", "from_t": 0.5, "to_segment": "s3", "to_t": 0.5, "amount": 6, "slash_id": "f"}
    after = run(BUS, before, "add_fullness", **params)
    assert _widths(after) == {"s1": 2.5, "s3": 1.2, "f.e1": 2.5, "f.b1": 2.5, "f.e2": 1.2, "f.b2": 1.2}
    GUARD.check(before, after)


def test_unfold_mirrors_widths_and_corners_and_fold_takes_them_back():
    before = _allowed(_style(), "back", {"s1": 2.5, "s4": 0}, {"b": "square"})
    unfolded = BUS.dispatch(before, History(), "unfold_piece", {"piece_id": "back", "suffix": ".m"})[0]
    allowance = unfolded.allowances[PieceId("back")]
    assert _widths(unfolded, "back") == {"s1": 2.5, "s1.m": 2.5}
    assert dict(allowance.corner_styles) == {PointId("b"): "square", PointId("b.m"): "square"}
    GUARD.check(before, unfolded)
    params = {"piece_id": "back", "start_id": "a", "end_id": "d", "segment_id": "s4"}
    folded = BUS.dispatch(unfolded, History(), "fold_piece", params)[0]
    assert folded.allowances[PieceId("back")].edge_widths == ((SegmentId("s1"), 2.5),)
    assert dict(folded.allowances[PieceId("back")].corner_styles) == {PointId("b"): "square"}
