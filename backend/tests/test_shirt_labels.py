"""T144: every 1078375 piece carries one label whose text comes only from the client PDS (name, quantity, fold)."""
import pytest
from shapely.geometry import Point, Polygon

from app.application.cad.style_from_block import style_from_block
from app.domain.pattern.cut_label import cut_text
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.edges import stitch_ring
from app.domain.pattern.style_codec import style_from_json, style_to_json

LABELS = {
    "FRT": "FRT · cut 2 (1 mirrored pair)", "back": "back · cut 1 on fold", "back YK": "back YK · cut 2 on fold",
    "CLR": "CLR · cut 2 on fold", "BND TOP": "BND TOP · cut 1 on fold", "BND IN": "BND IN · cut 1 on fold",
    "Sleeve": "Sleeve · cut 2 (1 mirrored pair)",
}


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


@pytest.mark.parametrize("size", ["S", "L", "3XL"])
def test_each_piece_has_its_sourced_label_inside_it(style, size):
    pieces = style.view(size)
    assert {piece.name: [label.text for label in piece.labels] for piece in pieces} == {
        name: [text] for name, text in LABELS.items()}
    for piece in pieces:
        outline = Polygon([(p.x, p.y) for p in stitch_ring(piece)])
        assert outline.contains(Point(piece.labels[0].position.x, piece.labels[0].position.y)), piece.name


def test_labels_survive_the_style_json_round_trip(style):
    restored = style_from_json(style_to_json(style))
    assert [p.labels for p in restored.view("L")] == [p.labels for p in style.view("L")]


@pytest.mark.parametrize(("cut", "text"), [
    (CutQuantity(1, 0, 0), "X · cut 1"), (CutQuantity(0, 2, 0), "X · cut 4 (2 mirrored pairs)"),
    (CutQuantity(1, 0, 1), "X · cut 2, 1 on fold"),
])
def test_the_cut_text_states_the_counts(cut, text):
    assert cut_text("X", cut) == text
