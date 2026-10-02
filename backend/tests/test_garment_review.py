"""P1-10 Gate B regressions: marks in a dart's V, asymmetric kept marks on fold, and clear refusals."""

from dataclasses import replace

import pytest
from garment_fixture import bodice, bodice_style, piece_of, run, seam_length
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole, Notch
from app.domain.pattern.ids import AnnotationId, GradeRuleId, PointId, SegmentId
from app.domain.pattern.piece_transform import reflection, transformed
from app.domain.pattern.size_pieces import SizePieces

DART = {"segment_id": "s1", "t_start": 0.4, "t_end": 0.5, "length": 15, "dart_id": "d1"}
ROTATE = {"apex_id": "d1.apex", "segment_id": "s2", "t": 0.6, "dart_id": "d2"}
FOLD_BACK = {"piece_id": "back", "start_id": "a", "end_id": "d", "segment_id": "s4"}


def _with(style, size="M", **changes):
    return style.with_piece(size, replace(piece_of(style, size), **changes))


def _drill(x, y, name="dot"):
    return (DrillHole(AnnotationId(name), Point2D(x, y), 0.3),)


def test_a_mark_inside_a_dart_is_refused_when_the_dart_turns_or_closes():
    darted = _with(run(BUS, bodice_style(), "create_dart", **DART), drills=_drill(18, 13))
    slash = {key: value for key, value in ROTATE.items() if key != "dart_id"}
    for command, ids in (("rotate_dart", {"dart_id": "d2"}), ("close_dart", {"slash_id": "k"})):
        with pytest.raises(ValueError, match="Size M: drill hole dot lies inside the dart at d1.apex"):
            run(BUS, darted, command, **slash, **ids)


def test_a_mark_the_new_dart_would_cut_out_is_refused():
    with pytest.raises(ValueError, match="Size M: drill hole dot lies inside the dart at d1.apex"):
        run(BUS, _with(bodice_style(), drills=_drill(18, 3)), "create_dart", **DART)


def test_a_notch_on_a_dart_leg_is_refused_by_name():
    darted = run(BUS, bodice_style(), "create_dart", **DART)
    notched = _with(darted, notches=(Notch(AnnotationId("ln"), SegmentId("d1.leg1"), 0.5),))
    with pytest.raises(ValueError, match="Size M: notch ln sits on a leg of the dart at d1.apex"):
        run(BUS, notched, "rotate_dart", **ROTATE)


def test_a_clockwise_piece_rotates_its_dart_and_keeps_seam_lengths():
    flipped = transformed(bodice(), reflection(Point2D(0, 0), Point2D(0, 1)))
    style = replace(bodice_style(), geometry={"S": SizePieces.from_pieces((flipped,)),
                                               "M": SizePieces.from_pieces((flipped,))})
    darted = run(BUS, style, "create_dart", **DART)
    after = run(BUS, darted, "rotate_dart", **ROTATE)
    assert seam_length(piece_of(after), ("d2.leg1", "d2.leg2")) == pytest.approx(
        seam_length(piece_of(darted), ("d1.leg1", "d1.leg2")), abs=0.01)
    GUARD.check(darted, after)


def _unfolded():
    return BUS.dispatch(_style(), History(), "unfold_piece", {"piece_id": "back", "suffix": ".m"})[0]


def test_a_kept_half_mark_without_a_mirror_is_refused_on_fold():
    style = _with(_unfolded(), drills=_drill(10, 10, "solo"))
    with pytest.raises(ValueError, match="Size M: drill hole solo on the kept half has no mirror"):
        BUS.dispatch(style, History(), "fold_piece", FOLD_BACK)


def test_fold_refuses_to_drop_a_graded_point():
    style = _unfolded()
    piece = piece_of(style)
    graded = tuple(replace(p, grade_rule=GradeRuleId("r1")) if p.id == PointId("b.m") else p for p in piece.points)
    with pytest.raises(ValueError, match="Size M: point b.m has a grade rule; folding would remove it"):
        BUS.dispatch(_with(style, points=graded), History(), "fold_piece", FOLD_BACK)


@pytest.mark.parametrize(
    ("command", "params", "match"),
    [
        ("slash_spread", {"hinge_id": "c", "segment_id": "s1", "t": 0.5, "angle_degrees": 180, "slash_id": "k"},
         "angle_degrees must be more than 0 and less than 180"),
        ("fold_piece", {"start_id": "a", "end_id": "a", "segment_id": "s9"}, "the fold needs two different points"),
    ],
)
def test_bad_values_get_the_domain_message_even_with_an_allowance(command, params, match):
    allowance = {"piece_id": "bodice", "default_width": 1, "edge_widths": {}, "corner_styles": {}}
    style = BUS.dispatch(bodice_style(), History(), "set_seam_allowance", allowance)[0]
    with pytest.raises(ValueError, match=match):
        run(BUS, style, command, **params)


def test_a_hinge_in_line_with_the_slash_is_refused_plainly():
    split = BUS.dispatch(bodice_style(), History(), "split_edge",
                         {"piece_id": "bodice", "segment_id": "s1", "t": 0.25, "point_id": "h", "new_segment_id": "s1b"})[0]
    with pytest.raises(ValueError, match="the hinge a and the slash are in line"):
        run(BUS, split, "slash_spread", hinge_id="a", segment_id="s1b", t=0.5, angle_degrees=10, slash_id="k")
