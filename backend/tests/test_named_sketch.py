"""T129: blocks draw pieces with named points and cubic Béziers between them (V6 model)."""
import pytest

from app.domain.blocks.sketch.naming import check_named, segment_id
from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.cutting import CutQuantity, FoldLine
from app.domain.pattern.ids import PointId
from app.domain.pattern.segment import CubicBezier, Line
from app.infrastructure.legacy_pattern_adapter import piece_from_v5

SPEC = PieceSpec("yoke", "Yoke", CutQuantity(0, 0, 1))
CURVE = (Vector2D(0, 2), Vector2D(-2, 0))


def _yoke() -> PieceSketch:
    return (PieceSketch().start("CB_neck", 0, 10).line_to("CB_yoke", 0, 0).line_to("SP", 12, 0)
            .curve_to("HPS", (6, 9), CURVE).close())


def test_a_sketch_builds_a_piece_whose_points_and_edges_are_named():
    piece = _yoke().fold("CB_neck", "CB_yoke").notch("shoulder_notch", "SP", "HPS", 0.5).build(SPEC)
    assert [str(p.id) for p in piece.points] == ["CB_neck", "CB_yoke", "SP", "HPS"]
    assert [str(s.id) for s in piece.outline] == ["CB_neck:CB_yoke", "CB_yoke:SP", "SP:HPS", "HPS:CB_neck"]
    curve = piece.outline[2]
    assert isinstance(curve, CubicBezier) and (curve.start_handle, curve.end_handle) == CURVE
    assert isinstance(piece.outline[3], Line) and piece.point(PointId("HPS")).position == Point2D(6, 9)
    assert piece.fold == FoldLine(segment_id("CB_neck", "CB_yoke"))
    assert (str(piece.notches[0].segment), piece.notches[0].t) == ("SP:HPS", 0.5)
    check_named(piece)


def test_closing_with_a_curve_and_a_grainline():
    piece = (PieceSketch().start("a", 0, 0).line_to("b", 10, 0).line_to("c", 10, 10)
             .close(CURVE).grain(Point2D(5, 1), Point2D(5, 9))
             .build(PieceSpec("p", "P", CutQuantity(0, 1, 0))))
    assert isinstance(piece.outline[-1], CubicBezier) and str(piece.outline[-1].id) == "c:a"
    assert piece.grainline is not None and piece.grainline.end == Point2D(5, 9)


@pytest.mark.parametrize("name", ["p3", "s12", "_neck", "CF__neck", "neck-line", "x" * 32, ""])
def test_a_point_needs_a_drafting_name(name):
    with pytest.raises(ValueError, match="must be a drafting name such as CF_neck"):
        PieceSketch().start(name, 0, 0)


def test_a_point_is_drawn_once():
    with pytest.raises(ValueError, match="Point SP is already drawn"):
        PieceSketch().start("SP", 0, 0).line_to("HPS", 1, 0).line_to("SP", 2, 2)


def test_an_open_outline_cannot_be_built():
    with pytest.raises(ValueError, match="Close the outline of Yoke before building it"):
        PieceSketch().start("a", 0, 0).line_to("b", 1, 0).line_to("c", 1, 1).build(SPEC)


def test_a_sketch_starts_once_and_draws_only_after_starting():
    with pytest.raises(ValueError, match="Start the outline before drawing to b"):
        PieceSketch().line_to("b", 1, 0)
    with pytest.raises(ValueError, match="The outline has already started"):
        PieceSketch().start("a", 0, 0).start("b", 1, 1)


def test_nothing_is_drawn_after_closing():
    with pytest.raises(ValueError, match="The outline is closed"):
        _yoke().line_to("extra", 3, 3)


def test_curve_handles_must_be_finite():
    with pytest.raises(ValueError, match="handles"):
        PieceSketch().start("a", 0, 0).curve_to("b", (5, 0), (Vector2D(float("nan"), 0), Vector2D(0, 0)))


def test_a_mark_on_an_edge_that_is_not_drawn_is_refused():
    with pytest.raises(ValueError, match="No edge SP to CB_neck"):
        _yoke().notch("n1", "SP", "CB_neck", 0.5)


def test_adapter_pieces_are_not_named():
    legacy = piece_from_v5({"id": "x", "name": "X", "points": [[0, 0], [1, 0], [1, 1], [0, 0]],
                            "quantity": 1, "grainline": [[0.2, 0.2], [0.8, 0.2]], "notches": []})
    with pytest.raises(ValueError, match="X has unnamed points: p0, p1, p2"):
        check_named(legacy.piece)
