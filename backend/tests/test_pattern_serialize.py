"""P1-02: a piece round-trips through deterministic JSON within 0.01 cm (Memento)."""

import json
from math import nan

import pytest
from test_pattern_piece import _piece

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole, InternalLine
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import AnnotationId
from app.domain.pattern.serialize import piece_from_data, piece_to_data
from app.domain.tolerances import LENGTH_CM


def _full_piece():
    line = InternalLine(AnnotationId("dart"), (Point2D(5, 5), Point2D(6.123456789, 12)))
    return _piece(internal_lines=(line,), drills=(DrillHole(AnnotationId("d1"), Point2D(8, 9), 0.4),))


def test_round_trip_keeps_every_element_within_tolerance():
    piece = _full_piece()
    restored = piece_from_data(json.loads(json.dumps(piece_to_data(piece))))
    assert restored.outline == piece.outline and restored.cut == piece.cut and restored.fold == piece.fold
    assert (
        restored.notches == piece.notches
        and restored.labels == piece.labels
        and restored.drills == piece.drills
    )
    for before, after in zip(piece.points, restored.points):
        assert before.id == after.id
        assert abs(before.position.x - after.position.x) <= LENGTH_CM
        assert abs(before.position.y - after.position.y) <= LENGTH_CM
    dart = restored.internal_lines[0].points[1]
    assert abs(dart.x - 6.123456789) <= LENGTH_CM


def test_serialization_is_deterministic_and_idempotent():
    data = piece_to_data(_full_piece())
    assert piece_to_data(piece_from_data(data)) == data
    assert json.dumps(data, sort_keys=True) == json.dumps(piece_to_data(_full_piece()), sort_keys=True)
    assert data["schema_version"] == 1 and [s["type"] for s in data["outline"]] == [
        "line",
        "cubic",
        "arc",
        "line",
    ]


def test_minimal_piece_without_optional_marks_round_trips():
    piece = _piece(fold=None, cut=CutQuantity(1, 0, 0), grainline=None, notches=(), labels=())
    assert piece_from_data(piece_to_data(piece)) == piece


def _broken(mutate):
    data = piece_to_data(_full_piece())
    mutate(data)
    return data


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.pop("outline"), "outline"),
        (lambda d: d.update(schema_version=2), "schema version"),
        (lambda d: d["outline"][1].update(type="spline"), "segment type"),
        (lambda d: d["points"][0].update(x=nan), "finite"),
        (lambda d: d["points"][0].update(x="0"), "finite"),
        (lambda d: d.update(points="abc"), "Invalid pattern data"),
        (lambda d: d["outline"].pop(), "not closed"),
        (lambda d: d["cut"].pop("on_fold"), "on_fold"),
        (lambda d: d.update(grainline=[]), "pair"),
        (lambda d: d.update(fold=""), "identifier"),
    ],
    ids=[
        "missing-outline",
        "schema",
        "segment-type",
        "nan",
        "string-number",
        "points-type",
        "open-outline",
        "missing-cut-field",
        "empty-grainline",
        "empty-fold",
    ],
)
def test_malformed_data_is_rejected(mutate, message):
    with pytest.raises(ValueError, match=message):
        piece_from_data(_broken(mutate))
