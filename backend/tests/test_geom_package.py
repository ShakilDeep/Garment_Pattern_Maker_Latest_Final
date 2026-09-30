"""domain.geometry stays a stable Facade over the responsibility-split domain.geom package."""
import importlib

import pytest

from app.domain import geometry

HOMES = {
    "primitives": ("EPSILON", "Point2D", "Vector2D", "LineSegment", "Polyline"),
    "curves": ("CubicBezier", "Arc"),
    "paths": ("ClosedPath", "BoundingBox"),
    "transform": ("Transform2D",),
    "polyline_ops": ("quadratic", "length", "area"),
    "piece_builder": ("make_piece", "unfold"),
}
ALL_NAMES = sorted(name for names in HOMES.values() for name in names)


@pytest.mark.parametrize("module_name,names", sorted(HOMES.items()))
def test_facade_re_exports_the_split_module_objects(module_name, names):
    module = importlib.import_module(f"app.domain.geom.{module_name}")
    for name in names:
        assert getattr(geometry, name) is getattr(module, name)


def test_facade_declares_exactly_the_public_geometry_api():
    assert sorted(geometry.__all__) == ALL_NAMES


def test_closed_path_bounds_still_use_bounding_box():
    path = geometry.ClosedPath((geometry.Point2D(0, 0), geometry.Point2D(4, 0), geometry.Point2D(0, 3)))
    assert (path.bounds.width, path.bounds.height) == (4, 3)


def test_make_piece_rejects_degenerate_outline():
    with pytest.raises(ValueError, match="Flat: invalid geometry"):
        geometry.make_piece("Flat", [[0, 0], [1, 0], [2, 0]])


def test_unfold_mirrors_half_outline_across_center_line_without_duplicating_it():
    half = [[0, 0], [1, 1], [2, 0]]
    assert geometry.unfold(half) == [[0, 0], [1, 1], [2, 0], [-1, 1], [0, 0]]
