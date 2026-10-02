"""P1-10 (CAD-03): unfold mirrors a piece about its fold edge; fold is its exact inverse on a symmetric piece."""

from dataclasses import replace

import pytest
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style
from test_draft_tools import _back

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import Notch
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.ids import AnnotationId, SegmentId

FOLD_BACK = {"start_id": "a", "end_id": "d", "segment_id": "s4"}


def _do(style, command, **params):
    return BUS.dispatch(style, History(), command, {"piece_id": "back", **params})[0]


def _unfolded():
    return _do(_style(), "unfold_piece", suffix=".m")


def test_unfold_mirrors_the_half_about_the_fold_and_cuts_it_once():
    piece = _back(_unfolded())
    assert [str(s.id) for s in piece.outline] == ["s1", "s2", "s3", "s3.m", "s2.m", "s1.m"]
    positions = {str(p.id): p.position for p in piece.points}
    assert positions["b.m"] == Point2D(-20, 0) and positions["c.m"] == Point2D(-20, 30)
    curve = piece.outline[4]
    assert (curve.start_handle, curve.end_handle) == (Vector2D(-5, -10), Vector2D(-5, 10))
    assert piece.outline[3].bulge == piece.outline[2].bulge
    assert piece.fold is None and piece.cut == CutQuantity(1, 0, 0)
    assert Notch(AnnotationId("n1.m"), SegmentId("s2.m"), 0.5) in piece.notches
    assert len(piece.labels) == 1 and piece.grainline == _back(_style()).grainline
    GUARD.check(_style(), _unfolded())


def test_folding_the_unfolded_piece_restores_it_exactly_in_every_size():
    folded = _do(_unfolded(), "fold_piece", **FOLD_BACK)
    for size in ("S", "M"):
        assert geometry_hash(_back(folded, size)) == geometry_hash(_back(_style(), size))


def _with_line_on_the_left(style):
    params = {"size": "M", "line_id": "pocket", "start": [-15, 10], "end": [-5, 10]}
    return _do(style, "add_line", **params)


def test_a_mark_without_a_mirrored_twin_on_the_kept_half_is_refused():
    with pytest.raises(ValueError, match="Size M: internal line pocket on the removed half has no mirror"):
        _do(_with_line_on_the_left(_unfolded()), "fold_piece", **FOLD_BACK)


def test_a_mark_with_its_twin_folds_away():
    style = _with_line_on_the_left(_unfolded())
    style = _do(style, "add_line", size="M", line_id="pocket2", start=[5, 10], end=[15, 10])
    folded = _back(_do(style, "fold_piece", **FOLD_BACK))
    assert [str(line.id) for line in folded.internal_lines] == ["pocket2"]


def test_an_asymmetric_piece_is_not_folded():
    moved = {"size": "M", "piece_id": "back", "point_id": "b.m", "x": -21, "y": 0}
    style = BUS.dispatch(_unfolded(), History(), "move_point", moved)[0]
    with pytest.raises(ValueError, match=r"Size M: the halves differ by [0-9.]+ cm; the piece is not symmetric about a-d"):
        _do(style, "fold_piece", **FOLD_BACK)


def test_unfold_refuses_a_piece_without_a_fold_or_with_a_notch_on_it():
    with pytest.raises(ValueError, match="Size S: Back has no fold edge to unfold"):
        _do(_unfolded(), "unfold_piece", suffix=".x")
    notched = _back(_style())
    notched = replace(notched, notches=(*notched.notches, Notch(AnnotationId("cf"), SegmentId("s4"), 0.5)))
    style = _style().with_piece("M", notched)
    with pytest.raises(ValueError, match="Size M: notch cf sits on the fold edge"):
        _do(style, "unfold_piece", suffix=".m")


@pytest.mark.parametrize(
    ("change", "error", "match"),
    [
        ({"segment_id": "s1"}, ValueError, "Segment id s1 is already used"),
        ({"end_id": "zz"}, KeyError, "zz"),
        ({"start_id": "d"}, ValueError, "the fold needs two different points"),
    ],
)
def test_bad_folds_are_refused(change, error, match):
    with pytest.raises(error, match=match):
        _do(_unfolded(), "fold_piece", **{**FOLD_BACK, **change})


def test_folding_a_piece_already_on_the_fold_is_refused():
    with pytest.raises(ValueError, match="Size S: Back is already cut on the fold"):
        _do(_style(), "fold_piece", start_id="a", end_id="c", segment_id="sx")
