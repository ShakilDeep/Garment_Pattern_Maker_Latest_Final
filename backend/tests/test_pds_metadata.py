"""T125 (M0): the Optitex PDS XML reader extracts sizes, base size, totals and piece metadata."""

import pytest


def _piece(style, name):
    return next(piece for piece in style.pieces if piece.name == name)


def test_shirt_1078375_matches_the_build_plan_numbers(pds_styles):
    shirt = pds_styles["1078375"]
    assert shirt.sizes == ("S", "M", "L", "XL", "XXL", "3XL")
    assert shirt.base_size == "L"
    assert len(shirt.pieces) == 7
    assert shirt.totals["L"].area_m2 == 1.4262
    assert shirt.optitex_version == "21.4.1103.0"


def test_pant_1074664_matches_the_build_plan_numbers(pds_styles):
    pant = pds_styles["1074664"]
    assert pant.sizes == ("XS", "S", "M", "L", "XL")
    assert pant.base_size == "S"
    assert len(pant.pieces) == 7
    assert pant.totals["S"].area_m2 == 1.8339


def test_piece_quantity_fold_and_rotation_rules(pds_styles):
    shirt = pds_styles["1078375"]
    front, back = _piece(shirt, "FRT"), _piece(shirt, "back")
    assert (front.quantity, front.on_fold, front.opposite) == (2, False, "Up/Down")
    assert (back.quantity, back.on_fold, back.opposite) == (1, True, "None")
    assert all(piece.rotation_deg == 180.0 for piece in shirt.pieces)


def test_per_size_geometry_is_read_for_every_size(pds_styles):
    front = _piece(pds_styles["1078375"], "FRT")
    assert tuple(front.geometry) == pds_styles["1078375"].sizes
    base = front.geometry["L"]
    assert (base.size_x_cm, base.size_y_cm, base.area_m2) == (78.888, 37.0748, 0.2588)
    assert (base.perimeter_cm, base.sew_area_m2, base.sew_perimeter_cm) == (223.5822, 0.225, 209.1049)


@pytest.mark.parametrize("style_number", ["1078375", "1074664"])
def test_piece_areas_times_quantity_sum_to_the_size_total(pds_styles, style_number):
    style = pds_styles[style_number]
    for size in style.sizes:
        total = sum(piece.geometry[size].area_m2 * piece.quantity for piece in style.pieces)
        assert total == pytest.approx(style.totals[size].area_m2, abs=0.0005), size


def test_a_piece_without_a_sew_line_has_no_sew_measurements(pds_styles):
    drawstring = _piece(pds_styles["1074664"], "DRAWSTRING")
    base = drawstring.geometry["S"]
    assert (base.size_x_cm, base.area_m2, base.sew_area_m2, base.sew_perimeter_cm) == (165.0, 0.066, None, None)
    assert drawstring.outline.sew == ()
