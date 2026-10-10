"""T129: a block drafts either a V5 dict (the demo) or named V6 pieces; client blocks must be named."""
import pytest
from pom_workbooks import BOOK2

from app.application.block_pieces import draft_block_pieces
from app.domain.blocks.base import NamedBlock, StyleOption
from app.domain.blocks.registry import BlockRegistry, installed
from app.domain.blocks.run import draft_pattern
from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.piece import Piece
from app.infrastructure.legacy_pattern_adapter import piece_from_v5
from app.infrastructure.parsers import parse_xlsx

SQUARE = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]


@pytest.fixture(scope="module")
def demo_values():
    rows = parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx")
    return {row["key"]: row["values"]["L"]["value"] for row in rows
            if row["values"].get("L", {}).get("value") is not None and row["mapping_status"] != "unmapped"}


def _named(width: float) -> Piece:
    return (PieceSketch().start("hem_cf", 0, 0).line_to("hem_side", width, 0).line_to("UA", width, 9)
            .line_to("CF_neck", 0, 9).close().build(PieceSpec("front", "Front", CutQuantity(0, 1, 0))))


class _Widen:
    option_id = "fit"

    def apply(self, pattern: tuple[Piece, ...], value: str) -> tuple[Piece, ...]:
        return (_named(14),) if value == "relaxed" else pattern


class _NamedShirt:
    id, version, family, calibration = "shirt_test", "1", "shirt", "client_approved"
    required: tuple[str, ...] = ("half_chest",)
    optional: tuple[str, ...] = ()
    options = (StyleOption("fit", "Fit", ("regular", "relaxed"), "regular"),)
    transforms = (_Widen(),)

    def __init__(self, pieces: tuple[Piece, ...] | None = None):
        self._pieces = pieces

    def draft_pieces(self, measurements, size, choices):
        return self._pieces or (_named(measurements["half_chest"] / 2),)


class _DictBlock(_NamedShirt):
    draft_pieces = None  # type: ignore[assignment]

    def draft(self, measurements, size, choices):
        return {"pieces": []}


def test_a_named_block_drafts_v6_pieces_with_its_style_choices():
    block = _NamedShirt()
    assert isinstance(block, NamedBlock)
    regular = draft_block_pieces(block, {"half_chest": 20}, "L", {})
    relaxed = draft_block_pieces(block, {"half_chest": 20}, "L", {"fit": "relaxed"})
    assert [str(p.id) for p in regular[0].points] == ["hem_cf", "hem_side", "UA", "CF_neck"]
    assert regular[0].points[1].position.x == 10 and relaxed[0].points[1].position.x == 14


def test_the_demo_block_still_reaches_v6_through_the_adapter(demo_values):
    block = installed().get("demo_v1")
    pieces = draft_block_pieces(block, demo_values, "L", {})
    expected = tuple(piece_from_v5(p).piece for p in draft_pattern(block, demo_values, "L", {})["pieces"])
    assert pieces == expected and str(pieces[0].points[0].id) == "p0"


def test_a_client_block_with_unnamed_points_is_refused():
    unnamed = piece_from_v5({"id": "front", "name": "Front", "points": SQUARE, "quantity": 1,
                             "grainline": [[1, 1], [1, 3]], "notches": []}).piece
    with pytest.raises(ValueError, match="Front has unnamed points: p0, p1, p2, p3"):
        draft_block_pieces(_NamedShirt((unnamed,)), {}, "L", {})


def test_a_named_block_has_no_v5_draft_yet():
    with pytest.raises(ValueError, match="Block shirt_test drafts named V6 pieces only"):
        draft_pattern(_NamedShirt(), {"half_chest": 20}, "L", {})


def test_a_client_block_must_be_a_named_block():
    with pytest.raises(ValueError, match="Client block shirt_test must draft named points"):
        BlockRegistry().register(_DictBlock())
    assert BlockRegistry().register(_NamedShirt()).id == "shirt_test"
