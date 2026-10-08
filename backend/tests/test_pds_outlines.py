"""T125 (M0): base-size SVG outlines become cm polygons whose areas match the PDS piece areas."""

import pytest
from shapely.geometry import LinearRing, Polygon

from app.infrastructure.pds.outline_geometry import area_m2, bounds_cm

AREA_TOLERANCE = 0.005  # build plan M0: within 0.5 %
BBOX_TOLERANCE_CM = 0.1
PIECES = [(style, index) for style, count in (("1078375", 7), ("1074664", 7)) for index in range(count)]


def _base(styles, style_number, index):
    style = styles[style_number]
    piece = style.pieces[index]
    return piece, piece.geometry[style.base_size]


@pytest.mark.parametrize(("style_number", "index"), PIECES)
def test_outline_area_is_within_half_a_percent_of_the_pds_area(pds_styles, style_number, index):
    piece, base = _base(pds_styles, style_number, index)
    assert area_m2(piece.outline) == pytest.approx(base.area_m2, rel=AREA_TOLERANCE), piece.name


@pytest.mark.parametrize(("style_number", "index"), PIECES)
def test_outline_bbox_matches_the_pds_piece_size(pds_styles, style_number, index):
    piece, base = _base(pds_styles, style_number, index)
    min_x, min_y, max_x, max_y = bounds_cm(piece.outline)
    assert max_x - min_x == pytest.approx(base.size_x_cm, abs=BBOX_TOLERANCE_CM), piece.name
    assert max_y - min_y == pytest.approx(base.size_y_cm, abs=BBOX_TOLERANCE_CM), piece.name


@pytest.mark.parametrize(("style_number", "index"), PIECES)
def test_cut_rings_are_valid_and_counter_clockwise(pds_styles, style_number, index):
    piece, _ = _base(pds_styles, style_number, index)
    assert len(piece.outline.cut) == (2 if piece.on_fold else 1)
    for ring in piece.outline.cut:
        assert Polygon(ring).is_valid
        assert LinearRing(ring).is_ccw


def test_on_fold_pieces_carry_a_fold_line_and_sew_lines(pds_styles):
    for style in pds_styles.values():
        for piece in style.pieces:
            assert bool(piece.outline.folds) == piece.on_fold, piece.name
            assert all(len(line) >= 2 for line in piece.outline.sew + piece.outline.folds)


def test_notch_marks_are_kept_in_centimetres(pds_styles):
    shirt_notches = [notch for piece in pds_styles["1078375"].pieces for notch in piece.outline.notches]
    assert len(shirt_notches) == 2
    (x0, y0), (x1, y1) = shirt_notches[0]
    assert ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 == pytest.approx(0.6964, abs=1e-4)
