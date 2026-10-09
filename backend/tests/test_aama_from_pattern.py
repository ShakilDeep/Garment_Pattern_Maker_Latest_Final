"""T127: the app pattern adapter copies what the piece has and invents nothing it lacks."""
import pytest

from app.infrastructure.aama.from_pattern import pattern_to_interchange

SQUARE = [[0, 0], [10, 0], [10, 20], [0, 20], [0, 0]]


def _pattern(**extra):
    piece = {"name": "Cuff", "quantity": 4, "points": SQUARE, "notches": [[10, 5]], **extra}
    return {"size": "L", "pieces": [piece]}


def test_rings_drop_the_closing_point_and_y_turns_up():
    piece = pattern_to_interchange(_pattern(grainline=[[5, 2], [5, 18]]), "Demo").pieces[0]
    assert piece.cut == ((0.0, 0.0), (10.0, 0.0), (10.0, -20.0), (0.0, -20.0))
    assert (piece.sew, piece.grain, piece.notches) == ((), ((5.0, -2.0), (5.0, -18.0)), (((10.0, -5.0),),))


@pytest.mark.parametrize("extra", [{}, {"grainline": None}])
def test_a_piece_without_a_grain_line_exports_without_one(extra):
    assert pattern_to_interchange(_pattern(**extra), "Demo").pieces[0].grain is None


def test_cut_points_make_points_the_sew_line():
    piece = pattern_to_interchange(_pattern(cut_points=SQUARE, grainline=None), "Demo").pieces[0]
    assert piece.sew == (piece.cut,)
