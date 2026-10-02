"""P1-05 (PM-04): a Style aggregate owns any number of pieces and sizes, with per-size views."""

from dataclasses import replace

import pytest
from test_pattern_piece import _piece

from app.domain.pattern.ids import PieceId, StyleId
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style

SIZES = ("4", "4½", "5")


def _pieces(*names):
    return tuple(replace(_piece(), id=PieceId(name), name=name.title()) for name in names)


def _style(**changes):
    fields = {
        "id": StyleId("shirt-01"),
        "name": "Oxford shirt",
        "sizes": SIZES,
        "base_size": "4½",
        "geometry": {"4½": SizePieces.from_pieces(_pieces("back", "front"))},
    }
    return Style(**{**fields, **changes})


def test_views_return_the_pieces_of_a_size_and_sizes_may_await_grading():
    style = _style()
    assert style.sizes == SIZES and style.piece_ids == (PieceId("back"), PieceId("front"))
    assert [p.name for p in style.view("4½")] == ["Back", "Front"]
    assert not style.has_geometry("5")
    with pytest.raises(ValueError, match="Size 5 has no pieces yet"):
        style.view("5")
    with pytest.raises(KeyError):
        style.view("6")


def test_with_pieces_returns_a_new_style_and_keeps_the_piece_list_aligned():
    style = _style()
    graded = style.with_pieces("5", _pieces("back", "front"))
    assert graded.has_geometry("5") and not style.has_geometry("5")
    with pytest.raises(ValueError, match="same pieces"):
        style.with_pieces("5", _pieces("front", "back"))
    with pytest.raises(KeyError):
        style.with_pieces("6", _pieces("back", "front"))


def test_the_only_sized_geometry_can_change_its_piece_list():
    style = _style().with_pieces("4½", _pieces("back", "front", "sleeve"))
    assert len(style.piece_ids) == 3


def test_a_style_may_start_without_pieces():
    assert _style(geometry={"4½": SizePieces.from_pieces(())}).piece_ids == ()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"sizes": ("4", "4")}, "more than once"),
        ({"sizes": ("4", "")}, "Size labels"),
        ({"sizes": ("4", " 5")}, "Size labels"),
        ({"sizes": ("4", 5)}, "Size labels"),
        ({"sizes": ()}, "at least one size"),
        ({"base_size": "6"}, "base size 6"),
        ({"geometry": {}}, "base size 4½ needs pieces"),
        ({"name": " "}, "needs a name"),
        ({"id": "shirt"}, "StyleId"),
    ],
)
def test_invalid_styles_are_refused(changes, message):
    with pytest.raises(ValueError, match=message):
        _style(**changes)


def test_geometry_must_belong_to_the_size_range_and_agree_on_pieces():
    base = SizePieces.from_pieces(_pieces("back", "front"))
    with pytest.raises(ValueError, match="not in the size range"):
        _style(geometry={"4½": base, "7": base})
    with pytest.raises(ValueError, match="same pieces"):
        _style(geometry={"4½": base, "5": SizePieces.from_pieces(_pieces("back"))})
    with pytest.raises(ValueError, match="Duplicate piece id"):
        SizePieces.from_pieces(_pieces("back", "back"))

