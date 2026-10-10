"""T130: the block's measurement set and shape constants are derived from the 1078375 PDS, never hand-typed."""
import json

import pytest

from app.domain.blocks.shirt.reference import MEASUREMENTS_FILE, reference_measurements
from app.domain.blocks.shirt.shape import SHAPE_FILE
from app.infrastructure.pds.shirt_derive import derive

FROM_SHIRT_DOC = {"front_length": 74.03, "half_chest_front": 31.36, "half_chest_back": 29.76, "back_length": 63.49,
                  "yoke_depth_cb": 12.04, "bicep": 43.86, "front_extension": 3.2, "collar_width_cb": 4.79,
                  "band_height_cb": 3.31, "sleeve_hem_width": 39.83, "hem_turnup": 2.0}


@pytest.fixture(scope="module")
def derived(pds_styles):
    return derive(pds_styles["1078375"])


def test_the_committed_data_is_exactly_what_the_pds_gives(derived):
    measurements, shape = derived
    assert json.loads(MEASUREMENTS_FILE.read_text(encoding="utf-8")) == measurements
    assert json.loads(SHAPE_FILE.read_text(encoding="utf-8")) == shape


def test_measurements_match_the_drafting_doc_and_name_their_source(derived):
    measurements, _ = derived
    for name, value in FROM_SHIRT_DOC.items():
        assert reference_measurements()[name] == pytest.approx(value, abs=1e-6), name
    assert all(entry["source"].startswith(("FRT", "back", "CLR", "BND", "Sleeve"))
               for entry in measurements["measurements"].values())
    assert measurements["source_pds"] == "1078375" and measurements["size"] == "L"


def test_a_pds_without_a_named_point_is_refused(pds_styles):
    style = pds_styles["1078375"]
    broken = type(style)(**{**style.__dict__, "pieces": tuple(p for p in style.pieces if p.name != "CLR")})
    with pytest.raises(ValueError, match="PDS has no piece CLR"):
        derive(broken)


def test_every_curve_follows_its_pds_run_within_the_agreed_tolerance(pds_styles):
    from app.domain.geom.bezier_fit import fit_cubic
    from app.domain.geom.primitives import Point2D
    from app.infrastructure.pds.shirt_named import named_pieces, smooth_ends

    for piece in named_pieces(pds_styles["1078375"]).values():
        for (start, end), kind in zip(piece.recipe.edges(), piece.recipe.kinds, strict=True):
            if kind == "cubic":
                samples = [Point2D(*point) for point in piece.run(start, end)]
                fit = fit_cubic(samples, smooth_ends(piece, start, end, samples))
                assert fit.max_deviation <= 0.1, (piece.recipe.id, start, end)  # docs/drafting/shirt.md Q4
