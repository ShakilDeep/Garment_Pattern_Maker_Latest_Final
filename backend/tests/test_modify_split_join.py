"""P1-09 (CAD-02): split cuts an edge in two and join is its exact inverse; notches stay where they were."""

from dataclasses import replace

import pytest
from test_cad_style_bus import BUS, _style
from test_draft_tools import _back

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D
from app.domain.pattern.edges import edge_polylines
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.ids import AnnotationId, GradeRuleId, PointId, SegmentId
from app.domain.pattern.notch_position import notch_position

REJOIN_CM = 1e-4


def _topology(style, command, **params):
    return BUS.dispatch(style, History(), command, {"piece_id": "back", **params})[0]


def _split(segment, t, style=None):
    return _topology(style or _style(), "split_edge", segment_id=segment, t=t, point_id="q", new_segment_id="sx")


def test_splitting_a_line_adds_a_point_and_joining_restores_the_piece_exactly():
    split = _back(_split("s1", 0.25))
    assert split.point(PointId("q")).position == Point2D(5, 0) and len(split.outline) == 5
    joined = _back(_topology(_split("s1", 0.25), "join_edges", point_id="q"))
    assert geometry_hash(joined) == geometry_hash(_back(_style()))


@pytest.mark.parametrize(("segment", "t"), [("s2", 0.25), ("s2", 0.8), ("s3", 0.3)])
def test_curves_split_and_rejoin_without_moving_their_shape_or_notches(segment, t):
    original = _back(_style())
    split = _back(_split(segment, t))
    notch = notch_position(split, split.notches[0])
    assert notch.x == pytest.approx(notch_position(original, original.notches[0]).x, abs=1e-6)
    assert notch.y == pytest.approx(notch_position(original, original.notches[0]).y, abs=1e-6)
    rejoined = _back(_topology(_split(segment, t), "join_edges", point_id="q"))
    for before, after in zip(edge_polylines(original), edge_polylines(rejoined)):
        # Bulges are stored to 1e-6, so a rejoined arc may be one quantum off (about 1e-5 cm here).
        assert all(abs(p.x - q.x) < REJOIN_CM and abs(p.y - q.y) < REJOIN_CM for p, q in zip(before, after))
    assert rejoined.notches[0].segment == SegmentId("s2") and rejoined.notches[0].id == AnnotationId("n1")


@pytest.mark.parametrize(
    ("command", "params", "message"),
    [
        ("split_edge", {"segment_id": "s4", "t": 0.5, "point_id": "q", "new_segment_id": "sx"}, "fold"),
        ("split_edge", {"segment_id": "s1", "t": 1, "point_id": "q", "new_segment_id": "sx"}, "between 0 and 1"),
        ("join_edges", {"point_id": "b"}, "do not continue one line, arc or curve"),
    ],
)
def test_bad_splits_and_joins_are_refused(command, params, message):
    with pytest.raises(ValueError, match=message):
        _topology(_style(), command, **params)


def test_a_point_with_a_grade_rule_is_not_joined_away():
    style = _split("s1", 0.5)
    back = _back(style)
    points = tuple(replace(p, grade_rule=GradeRuleId("r1")) if p.id == PointId("q") else p for p in back.points)
    graded = style.with_piece("M", replace(back, points=points))
    with pytest.raises(ValueError, match="grade rule"):
        _topology(graded, "join_edges", point_id="q")
