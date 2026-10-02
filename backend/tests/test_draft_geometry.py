"""P1-08: offset mitres, winding and refused constructions, checked against exact geometry."""

from math import atan, cos, hypot, sin

import pytest
from test_cad_style_bus import BUS
from test_draft_tools import _back, _run

from app.application.cad.history import History
from app.domain.geom.curves import CURVE_STEPS
from app.domain.geom.primitives import Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style


def test_curved_offsets_are_mitred_at_every_sampled_bend():
    distance, bulge, chord = 0.5, 0.4, 20
    angle = 4 * atan(bulge)
    radius = chord / (2 * sin(angle / 2))
    centre = Point2D(10, 30 + bulge * chord / 2 - radius)
    line = _back(_run("offset_edge", segment_id="s3", distance=distance, line_id="o")).internal_lines[-1]
    half_step = angle / CURVE_STEPS / 2
    for point in line.points[1:-1]:
        assert hypot(point.x - centre.x, point.y - centre.y) == pytest.approx(radius + distance / cos(half_step))


def test_outside_follows_the_winding_of_a_clockwise_piece():
    corners = {"a": (0, 0), "b": (0, 10), "c": (10, 10), "d": (10, 0)}
    points = tuple(PatternPoint(PointId(k), Point2D(*v)) for k, v in corners.items())
    names = list(corners)
    outline = tuple(Line(SegmentId(f"s{i}"), PointId(names[i]), PointId(names[(i + 1) % 4])) for i in range(4))
    piece = Piece(PieceId("cw"), "Clockwise", points, outline, CutQuantity(1, 0, 0))
    style = Style(StyleId("cw"), "Clockwise", ("M",), "M", {"M": SizePieces.from_pieces((piece,))})
    params = {"size": "M", "piece_id": "cw", "segment_id": "s0", "distance": 1, "line_id": "o"}
    offset = BUS.dispatch(style, History(), "offset_edge", params)[0].view("M")[0].internal_lines[-1]
    assert offset.points == (Point2D(-1, 0), Point2D(-1, 10))


@pytest.mark.parametrize(
    ("command", "params", "message"),
    [
        ("offset_edge", {"segment_id": "s1", "distance": 1e-9, "line_id": "o"}, "non-zero"),
        ("offset_edge", {"segment_id": "s3", "distance": -50, "line_id": "o"}, "folds the line over itself"),
        ("parallel_line", {"segment_id": "s1", "through": [5, 0], "line_id": "p"}, "only copy the line"),
        ("curve_edge", {"segment_id": "s4", "start_handle": [1, 1], "end_handle": [1, 1]}, "fold"),
    ],
)
def test_degenerate_constructions_are_refused(command, params, message):
    with pytest.raises(ValueError, match=message):
        _run(command, **params)


def test_nearly_parallel_lines_do_not_meet_far_away():
    style, history = BUS.dispatch(*_line_on_back("near", [0, 5], [20, 5.000001]))
    with pytest.raises(ValueError, match="parallel"):
        BUS.dispatch(style, history, "intersection_point",
                     {"size": "M", "piece_id": "back", "first": "s1", "second": "near", "point_id": "x"})


def _line_on_back(line_id, start, end):
    from test_cad_style_bus import _style

    params = {"size": "M", "piece_id": "back", "line_id": line_id, "start": start, "end": end}
    return _style(), History(), "add_line", params
