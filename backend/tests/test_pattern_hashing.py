"""P1-02: the geometry hash is stable, deterministic and sensitive only to real geometry changes."""

from test_pattern_piece import P, _piece

from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.serialize import piece_from_data, piece_to_data

# Pinned: an accidental change to the serialized form would break undo history and grading.
# To change the form deliberately, bump serialize.SCHEMA_VERSION and re-pin with:
#   cd backend && PYTHONPATH=.:tests python -c "from test_pattern_piece import _piece;
#   from app.domain.pattern.hashing import geometry_hash; print(geometry_hash(_piece()))"
GOLDEN = "ce1aaa82f4329435c1b4970510e4c431e51cd527f6655d87d1a82a34aeece4b8"


def test_equal_pieces_share_a_hash_and_survive_a_round_trip():
    piece = _piece()
    assert (
        geometry_hash(piece)
        == geometry_hash(_piece())
        == geometry_hash(piece_from_data(piece_to_data(piece)))
    )
    assert len(geometry_hash(piece)) == 64


def test_hash_is_pinned_across_runs():
    assert geometry_hash(_piece()) == GOLDEN


def test_sub_tolerance_noise_does_not_change_the_hash():
    piece = _piece()
    assert geometry_hash(piece.move_point(P["c"], 20 + 1e-9, 30)) == geometry_hash(piece)


def test_real_edits_change_the_hash():
    piece = _piece()
    assert geometry_hash(piece.move_point(P["c"], 20.01, 30)) != geometry_hash(piece)
    assert geometry_hash(_piece(cut=CutQuantity(1, 0, 1))) != geometry_hash(piece)


def test_negative_zero_and_unicode_text_hash_deterministically():
    piece = _piece(name="Dos · পেছন")
    assert geometry_hash(piece.move_point(P["a"], -0.0, -1e-8)) == geometry_hash(piece)
    assert geometry_hash(piece) == geometry_hash(piece_from_data(piece_to_data(piece)))
