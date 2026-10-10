"""T130: the 1078375 ShirtBlock drafts the seven PDS pieces with the named points of docs/drafting/shirt.md."""
import pytest

from app.domain.blocks.base import NamedBlock
from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_named
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.segment import CubicBezier

POINTS = {
    "FRT": ["FE_top", "CF_top", "CF_neck", "HPS", "SP", "UA", "side_hem", "FE_hem"],
    "back": ["CB_yoke", "yoke_armhole", "UA", "side_hem", "CB_hem"],
    "back_YK": ["CB_neck", "HPS", "SP", "yoke_armhole", "CB_yoke"],
    "CLR": ["CB_collar_neck", "collar_neck_end", "collar_point", "CB_collar_outer"],
    "BND_TOP": ["CB_band_top", "band_top_end", "band_neck_end", "CB_band_neck"],
    "BND_IN": ["CB_band_top", "band_top_end", "band_neck_end", "CB_band_neck"],
    "Sleeve": ["hem_fold_back", "UA_back", "cap_crown", "UA_front", "hem_fold_front", "hem_front", "hem_back"],
}
LINES = {"FE_top:CF_top", "CF_top:CF_neck", "HPS:SP", "FE_hem:FE_top", "CB_hem:CB_yoke", "yoke_armhole:CB_yoke",
         "CB_yoke:CB_neck", "collar_neck_end:collar_point", "CB_collar_outer:CB_collar_neck",
         "CB_band_neck:CB_band_top", "hem_fold_front:hem_front", "hem_front:hem_back", "hem_back:hem_fold_back"}
CUTS = {"FRT": (0, 1, 0), "back": (0, 0, 1), "back_YK": (0, 0, 2), "CLR": (0, 0, 2), "BND_TOP": (0, 0, 1),
        "BND_IN": (0, 0, 1), "Sleeve": (0, 1, 0)}
FOLDS = {"back": "CB_hem:CB_yoke", "back_YK": "CB_yoke:CB_neck", "CLR": "CB_collar_outer:CB_collar_neck",
         "BND_TOP": "CB_band_neck:CB_band_top", "BND_IN": "CB_band_neck:CB_band_top"}


@pytest.fixture(scope="module")
def pieces():
    return {str(p.id): p for p in draft_named(installed().get("shirt_1078375"), reference_measurements(), "L", {})}


def test_the_block_is_an_installed_client_named_block_not_offered_to_v5_projects():
    block = installed().get("shirt_1078375")
    assert isinstance(block, NamedBlock) and (block.family, block.calibration) == ("shirt", "client_approved")
    assert all(option.fixed for option in block.options)
    assert "shirt_1078375" not in installed().project_ids() and "demo_v1" in installed().project_ids()


def test_seven_pieces_with_the_pds_names_and_cuts(pieces):
    assert list(pieces) == list(POINTS)
    assert [p.name for p in pieces.values()] == ["FRT", "back", "back YK", "CLR", "BND TOP", "BND IN", "Sleeve"]
    for piece_id, cut in CUTS.items():
        assert pieces[piece_id].cut == CutQuantity(*cut)


def test_points_edges_and_folds_follow_the_drafting_doc(pieces):
    for piece_id, names in POINTS.items():
        piece = pieces[piece_id]
        assert [str(p.id) for p in piece.points] == names
        assert [str(s.id) for s in piece.outline] == [f"{a}:{b}" for a, b in zip(names, names[1:] + names[:1])]
        for segment in piece.outline:
            assert isinstance(segment, CubicBezier) == (str(segment.id) not in LINES), segment.id
        assert (str(piece.fold.segment) if piece.fold else None) == FOLDS.get(piece_id)


def test_only_the_two_pds_notches_and_grain_along_x(pieces):
    notches = {(pid, str(n.id), str(n.segment)) for pid, p in pieces.items() for n in p.notches}
    assert notches == {("back_YK", "shoulder_notch", "HPS:SP"), ("Sleeve", "crown_notch", "cap_crown:UA_front")}
    for piece in pieces.values():
        assert piece.grainline is not None and piece.grainline.start.y == piece.grainline.end.y


def test_a_missing_or_non_positive_measurement_is_named():
    values = {**reference_measurements(), "bicep": 0}
    del values["cap_height"]
    with pytest.raises(ValueError, match="Missing or non-positive shirt measurements: bicep, cap_height"):
        installed().get("shirt_1078375").draft_pieces(values, "L", {})
