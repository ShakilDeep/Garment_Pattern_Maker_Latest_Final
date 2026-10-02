"""P1-09 regressions: split/join keep the cut line and every size aligned; joins accept only one shape."""

from dataclasses import replace

import pytest
from shapely.geometry import Polygon
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style
from test_modify_split_join import REJOIN_CM, _split, _topology

from app.application.cad.history import History
from app.domain.pattern.edges import edge_polylines
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.segment import Arc
from app.domain.pattern.size_pieces import SizePieces
from app.infrastructure.piece_validity import check_cut_geometry

ALLOWANCE = SeamAllowance(1, ((SegmentId("s1"), 2.5), (SegmentId("s4"), 0)))


def _cut_area(style, size="M"):
    piece = style.view(size)[0]
    return Polygon([(p.x, p.y) for p in check_cut_geometry(piece, style.allowances[piece.id])]).area


def test_split_reaches_every_size_and_keeps_the_cut_line():
    style = _style().with_allowance(PieceId("back"), ALLOWANCE)
    split = _split("s1", 0.5, style)
    GUARD.check(style, split)
    assert all(PointId("q") in {p.id for p in split.view(size)[0].points} for size in ("S", "M"))
    assert split.allowances[PieceId("back")].width_of(SegmentId("sx")) == 2.5
    assert _cut_area(split) == pytest.approx(_cut_area(style), abs=1e-6)


def test_join_needs_one_width_and_then_drops_the_second_entry():
    split = _split("s1", 0.5, _style().with_allowance(PieceId("back"), ALLOWANCE))
    uneven = split.with_allowance(PieceId("back"), SeamAllowance(1, ((SegmentId("s1"), 2.5),)))
    with pytest.raises(ValueError, match="different seam allowances"):
        _topology(uneven, "join_edges", point_id="q")
    cornered = split.with_allowance(PieceId("back"), SeamAllowance(
        1, split.allowances[PieceId("back")].edge_widths, ((PointId("q"), "square"),)))
    joined = _topology(cornered, "join_edges", point_id="q")
    assert dict(joined.allowances[PieceId("back")].edge_widths) == {SegmentId("s1"): 2.5, SegmentId("s4"): 0}
    assert joined.allowances[PieceId("back")].corner_styles == ()
    with pytest.raises(KeyError):
        _topology(cornered, "join_edges", point_id="nope")


def _with_arc(bulge, notch_t=None):
    style = _style()
    back = style.view("M")[0]
    outline = tuple(Arc(s.id, s.start, s.end, bulge) if s.id == SegmentId("s3") else s for s in back.outline)
    notches = back.notches if notch_t is None else (replace(back.notches[0], segment=SegmentId("s3"), t=notch_t),)
    changed = SizePieces.from_pieces((replace(back, outline=outline, notches=notches), style.view("M")[1]))
    return replace(style, geometry={"S": changed, "M": changed})


def test_a_shallow_arc_split_near_its_end_rejoins():
    original = _with_arc(0.01)
    rejoined = _topology(_split("s3", 0.05, original), "join_edges", point_id="q").view("M")[0]
    for before, after in zip(edge_polylines(original.view("M")[0]), edge_polylines(rejoined)):
        assert all(abs(p.x - q.x) < REJOIN_CM and abs(p.y - q.y) < REJOIN_CM for p, q in zip(before, after))


def test_an_arc_notch_stays_where_it_was():
    from app.domain.pattern.notch_position import notch_position

    original = _with_arc(0.4, notch_t=0.6)
    split = _split("s3", 0.3, original).view("M")[0]
    before, after = notch_position(original.view("M")[0], original.view("M")[0].notches[0]), notch_position(
        split, split.notches[0])
    assert (after.x, after.y) == pytest.approx((before.x, before.y), abs=1e-5)
    assert split.notches[0].segment == SegmentId("sx")


@pytest.mark.parametrize(
    ("prepare", "point"),
    [
        (lambda: _curved_s3(), "c"),
        (lambda: _moved(_split("s1", 0.5), "q", 10, 1), "q"),
        (lambda: _moved(_split("s3", 0.5), "q", 10, 36), "q"),
    ],
)
def test_edges_that_are_not_one_shape_are_not_joined(prepare, point):
    with pytest.raises(ValueError, match="do not continue one line, arc or curve"):
        _topology(prepare(), "join_edges", point_id=point)


def _curved_s3():
    params = {"size": "S", "piece_id": "back", "segment_id": "s3", "start_handle": [-2, 6], "end_handle": [4, 3]}
    style = BUS.dispatch(_style(), History(), "curve_edge", params)[0]
    return BUS.dispatch(style, History(), "curve_edge", {**params, "size": "M"})[0]


def _moved(style, point, x, y):
    for size in ("S", "M"):
        params = {"size": size, "piece_id": "back", "point_id": point, "x": x, "y": y}
        style = BUS.dispatch(style, History(), "move_point", params)[0]
    return style
