"""T129: seam lengths are walked along named points, so blocks can true their seams (accuracy suite)."""
import pytest

from app.domain.blocks.sketch.named_edges import edge, path_length, seam_gap
from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.geom.curves import CubicBezier as GeomCubic
from app.domain.geom.polyline_ops import length
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.cutting import CutQuantity

SPEC = PieceSpec("p", "Panel", CutQuantity(1, 0, 0))
HANDLES = (Vector2D(0, 4), Vector2D(-3, 0))


def _panel(width: float = 10) -> object:
    return (PieceSketch().start("hem_cf", 0, 0).line_to("hem_side", width, 0)
            .curve_to("UA", (width, 8), HANDLES).line_to("CF_neck", 0, 8).close().build(SPEC))


def test_edge_finds_a_segment_by_its_named_ends():
    assert str(edge(_panel(), "hem_side", "UA").id) == "hem_side:UA"


def test_path_length_walks_lines_and_curves():
    curve = GeomCubic(Point2D(10, 0), Point2D(10, 4), Point2D(7, 8), Point2D(10, 8))
    sampled = length([(p.x, p.y) for p in curve.sample(4096)])
    assert path_length(_panel(), ("hem_cf", "hem_side")) == pytest.approx(10)
    assert path_length(_panel(), ("hem_side", "UA")) == pytest.approx(sampled, abs=1e-4)
    assert path_length(_panel(), ("hem_cf", "hem_side", "UA")) == pytest.approx(10 + sampled, abs=1e-4)


def test_seam_gap_is_zero_for_seams_of_equal_length_and_signed_otherwise():
    assert seam_gap((_panel(), ("hem_cf", "hem_side")), (_panel(), ("hem_cf", "hem_side"))) == 0
    assert seam_gap((_panel(12), ("hem_cf", "hem_side")), (_panel(), ("hem_cf", "hem_side"))) == pytest.approx(2)


def test_an_edge_that_is_not_drawn_is_a_key_error():
    with pytest.raises(KeyError, match="No edge UA to hem_cf on Panel"):
        edge(_panel(), "UA", "hem_cf")


def test_a_path_needs_two_points():
    with pytest.raises(ValueError, match="A seam path needs at least two named points"):
        path_length(_panel(), ("UA",))
