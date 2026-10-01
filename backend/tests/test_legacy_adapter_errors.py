"""P1-03: malformed V5 pieces and V6-only geometry are rejected with ValueError, never guessed."""

from math import nan

import pytest

from app.infrastructure.legacy_pattern_adapter import piece_from_v5, piece_to_v5
from app.infrastructure.legacy_piece import LegacyPiece

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]


def _v5(**changes):
    piece = {
        "id": "square",
        "name": "Square",
        "points": SQUARE,
        "quantity": 2,
        "grainline": [[5, 2], [5, 8]],
        "notches": [[10, 0], [4, 10]],
        "seams": {},
    }
    return {**piece, **changes}


def test_vertex_and_mid_edge_notches_are_anchored_on_their_segments():
    notches = piece_from_v5(_v5()).piece.notches
    assert [(str(n.segment), n.t) for n in notches] == [("s0", 1.0), ("s2", 0.6)]
    assert piece_to_v5(piece_from_v5(_v5()))["notches"] == [[10, 0], [4, 10]]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"points": SQUARE[:-1]}, "closed"),
        ({"points": [[0, 0], [10, 0], [0, 0]]}, "outline"),
        ({"points": "abc"}, "closed"),
        ({"notches": [[5, 5]]}, "not on the outline"),
        ({"notches": [[5]]}, "pair"),
        ({"quantity": 0}, "cut quantity"),
        ({"quantity": True}, "cut quantity"),
        ({"grainline": None}, "pair"),
        ({"id": "has space"}, "identifier"),
        ({"seams": {"armhole": nan}}, "Invalid V5 piece"),
        ({"points": [[0, 0], [10, nan], [10, 10], [0, 0]]}, "finite"),
    ],
    ids=["open", "degenerate", "points-type", "loose-notch", "short-notch", "zero-quantity",
         "bool-quantity", "no-grainline", "bad-id", "nan-extra", "nan-point"],
)
def test_malformed_v5_pieces_raise_value_error(changes, message):
    with pytest.raises(ValueError, match=message):
        piece_from_v5(_v5(**changes))


@pytest.mark.parametrize("missing", ["id", "name", "points", "quantity", "grainline", "notches"])
def test_missing_v5_fields_are_named(missing):
    data = _v5()
    del data[missing]
    with pytest.raises(ValueError, match=f"missing field '{missing}'"):
        piece_from_v5(data)


def test_huge_coordinates_and_deep_extras_raise_value_error():
    with pytest.raises(ValueError, match="too large"):
        piece_from_v5(_v5(points=[[0, 0], [1e200, 0], [1e200, 1e200], [0, 0]], notches=[[1e199, 0]]))
    deep: list = []
    for _ in range(200_000):  # deeper than the C JSON encoder recurses
        deep = [deep]
    with pytest.raises(ValueError, match="Invalid V5 piece"):
        piece_from_v5(_v5(seams=deep))


def test_non_object_input_is_rejected():
    with pytest.raises(ValueError, match="object"):
        piece_from_v5([1, 2])  # type: ignore[arg-type]


@pytest.mark.parametrize("extras", ['{"points": []}', "[]", "not json", '{"x": NaN}', b"{}"])
def test_extras_must_be_a_json_object_without_model_fields(extras):
    with pytest.raises(ValueError, match="extras"):
        LegacyPiece(piece_from_v5(_v5()).piece, extras)
