"""P1-02: values near the 1e-6 cm quantization step behave the same before and after a round trip."""

import pytest
from test_pattern_piece import P, _outline, _piece
from test_pattern_serialize import _broken

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole
from app.domain.pattern.ids import AnnotationId, GradeRuleId, SegmentId
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Arc
from app.domain.pattern.serialize import piece_from_data, piece_to_data


def _with_arc_bulge(bulge):
    outline = list(_outline())
    outline[2] = Arc(SegmentId("s3"), P["c"], P["d"], bulge)
    return _piece(outline=tuple(outline))


@pytest.mark.parametrize(
    "build",
    [
        lambda: _with_arc_bulge(6e-7),
        lambda: _piece().move_point(P["b"], 2.4e-6, 0),
        lambda: _piece(drills=(DrillHole(AnnotationId("d1"), Point2D(1, 1), 6e-7),)),
    ],
    ids=["tiny-bulge", "near-coincident", "tiny-drill"],
)
def test_near_threshold_pieces_round_trip_exactly(build):
    piece = build()
    assert piece_from_data(piece_to_data(piece)) == piece


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: _with_arc_bulge(4e-7), "non-zero bulge"),
        (lambda: _piece().move_point(P["b"], 1.4e-6, 0), "coincident"),
        (lambda: DrillHole(AnnotationId("d1"), Point2D(1, 1), 4e-7), "positive diameter"),
    ],
    ids=["bulge-rounds-to-zero", "gap-rounds-to-tolerance", "drill-rounds-to-zero"],
)
def test_values_that_quantize_away_are_rejected_at_construction(build, message):
    with pytest.raises(ValueError, match=message):
        build()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["points"][0].update(x=10**400), "finite"),
        (lambda d: d.update(grainline=[[0, 0]]), "pair"),
        (lambda d: d["drills"].append({"id": "d9", "at": [1, 2, 3], "diameter": 1}), "pair"),
        (lambda d: d["points"][0].update(grade_rule=""), "identifier"),
        (lambda d: d.update(schema_version=True), "schema version"),
    ],
    ids=["overflow-int", "short-grainline", "triple-at", "empty-grade-rule", "bool-schema"],
)
def test_malformed_values_raise_value_error(mutate, message):
    with pytest.raises(ValueError, match=message):
        piece_from_data(_broken(mutate))


def test_grade_rule_round_trips_and_must_be_typed():
    graded = PatternPoint(P["zz"], Point2D(5, 5), GradeRuleId("rule-1"))
    piece = _piece(points=(*_piece().points, graded))
    assert piece_from_data(piece_to_data(piece)).points[-1].grade_rule == GradeRuleId("rule-1")
    with pytest.raises(ValueError, match="GradeRuleId"):
        PatternPoint(P["zz"], Point2D(5, 5), "rule-1")  # type: ignore[arg-type]
