"""P1-03: V5 piece dicts round-trip through the Strangler Fig adapter, and the V5 goldens hold through it."""

import pytest
from test_demo_goldens import values_for

from app.domain.catalog import SIZES
from app.domain.drafting import draft
from app.domain.pattern.hashing import geometry_hash
from app.infrastructure.geometry_adapter import apply_allowance
from app.infrastructure.legacy_pattern_adapter import (
    draft_pieces,
    pattern_with_pieces,
    piece_from_v5,
    piece_to_v5,
)
from app.infrastructure.validation import validate

GRID_CM = 1e-6  # the model's quantization step: the only drift allowed, and only on the grainline
MOVABLE = ("grainline",)


def _within_grid(before, after):
    assert len(before) == len(after)
    for (x0, y0), (x1, y1) in zip(before, after):
        assert abs(x0 - x1) <= GRID_CM and abs(y0 - y1) <= GRID_CM


def _assert_round_trip(original):
    legacy = piece_from_v5(original)
    restored = piece_to_v5(legacy)
    assert restored.keys() == original.keys()
    assert {k: v for k, v in restored.items() if k not in MOVABLE} == {
        k: v for k, v in original.items() if k not in MOVABLE
    }
    for key in MOVABLE:
        _within_grid(original[key], restored[key])
    again = piece_from_v5(restored)
    assert again == legacy and geometry_hash(again.piece) == geometry_hash(legacy.piece)
    assert piece_to_v5(again) == restored


@pytest.mark.parametrize("size", SIZES)
def test_every_drafted_piece_round_trips(rows, size):
    for piece in draft(values_for(rows, size), size)["pieces"]:
        _assert_round_trip(piece)


@pytest.mark.parametrize("size", SIZES)
def test_seam_allowance_cut_outline_survives_the_round_trip(rows, size):
    pattern = draft(values_for(rows, size), size)
    apply_allowance(pattern, 1.0)
    for piece in pattern["pieces"]:
        _assert_round_trip(piece)


def test_v5_cut_data_maps_without_inventing_rules(rows):
    by_name = {p.piece.name: p for p in draft_pieces(values_for(rows, "M"), "M")}
    front, back = by_name["Front"], by_name["Back"]
    assert (front.piece.cut.single, front.piece.cut.mirrored_pairs, front.piece.cut.on_fold) == (2, 0, 0)
    assert back.piece.fold is None and back.extra_fields()["cut_on_fold"] is True
    assert by_name["Sleeve"].extra_fields()["marks"][0]["kind"] == "placket"


@pytest.mark.parametrize("size", SIZES)
def test_v5_goldens_and_validation_hold_through_the_adapter(rows, golden, size):
    values = values_for(rows, size)
    pattern = draft(values, size)
    rebuilt = pattern_with_pieces(pattern, draft_pieces(values, size))
    for piece in rebuilt["pieces"]:
        metrics = golden["sizes"][size]["pieces"][piece["id"]]
        for key in ("width", "height", "area", "perimeter"):
            assert piece[key] == pytest.approx(metrics[key], abs=1e-6, rel=0), (size, piece["id"], key)
        assert piece["seams"] == pytest.approx(metrics["seams"], abs=1e-6, rel=0)
        assert piece["quantity"] == metrics["quantity"]
    assert validate(rebuilt) == validate(pattern)
    assert {k: v for k, v in rebuilt.items() if k != "pieces"} == {
        k: v for k, v in pattern.items() if k != "pieces"
    }
