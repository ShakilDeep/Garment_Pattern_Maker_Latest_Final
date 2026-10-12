"""T130: every edge of the 1078375 block takes its confirmed finishing role (finishing.json, PDS measured)."""
import pytest

from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_named
from app.domain.blocks.shirt.allowances import seam_allowance
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.finishing import finishing
from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.ids import SegmentId

WIDTHS = {
    ("FRT", "FE_top:CF_top"): 1.0, ("FRT", "CF_top:CF_neck"): 0.0, ("FRT", "side_hem:FE_hem"): 3.5,
    ("FRT", "FE_hem:FE_top"): 1.7, ("FRT", "UA:side_hem"): 0.8, ("back", "UA:side_hem"): 1.7,
    ("back", "CB_hem:CB_yoke"): 0.0, ("Sleeve", "hem_fold_front:hem_front"): 0.8,
    ("Sleeve", "hem_back:hem_fold_back"): 1.7, ("Sleeve", "cap_crown:UA_front"): 2.0, ("CLR", "collar_point:CB_collar_outer"): 1.3,
}


@pytest.fixture(scope="module")
def pieces():
    return draft_named(installed().get("shirt_1078375"), reference_measurements(), "L", {})


def test_every_edge_has_an_explicit_width_and_the_fold_has_none(pieces):
    for piece in pieces:
        allowance = seam_allowance(str(piece.id))
        assert {seg for seg, _ in allowance.edge_widths} == {s.id for s in piece.outline}, piece.id
        if piece.fold:
            assert allowance.width_of(piece.fold.segment) == 0


@pytest.mark.parametrize(("key", "width"), WIDTHS.items(), ids=[f"{p}-{e}" for p, e in WIDTHS])
def test_widths_are_the_finishing_values(key, width):
    assert seam_allowance(key[0]).width_of(SegmentId(key[1])) == width


def test_every_corner_takes_the_finishing_corner_style(pieces):
    style = CornerStyle(finishing().families["shirt"].corner)
    for piece in pieces:
        corners = dict(seam_allowance(str(piece.id)).corner_styles)
        assert set(corners) == {segment.start for segment in piece.outline}, piece.id
        assert set(corners.values()) == {style}


def test_an_unknown_piece_is_a_key_error():
    with pytest.raises(KeyError, match="The 1078375 block has no piece pocket"):
        seam_allowance("pocket")
