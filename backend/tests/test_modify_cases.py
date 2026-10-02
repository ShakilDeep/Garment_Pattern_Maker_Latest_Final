"""P1-09 edge cases: wrap-around joins, multi-point trims, smoothing against an arc, mirrored labels."""

from dataclasses import replace

import pytest
from test_cad_style_bus import BUS, _style
from test_draft_tools import _back
from test_modify_split_join import _topology
from test_modify_transform import _run
from test_modify_trim_extend import _with_line

from app.application.cad.history import History
from app.domain.geom.lines import cross, unit
from app.domain.geom.primitives import Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PieceId, PointId, SegmentId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Line
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style
from app.domain.pattern.tangents import end_tangents


def test_a_join_across_the_outline_start_closes_the_ring():
    corners = {"m": (10, 0), "b": (20, 0), "c": (20, 10), "d": (0, 10), "a": (0, 0)}
    names = list(corners)
    points = tuple(PatternPoint(PointId(k), Point2D(*v)) for k, v in corners.items())
    outline = tuple(Line(SegmentId(f"s{i}"), PointId(names[i]), PointId(names[(i + 1) % 5])) for i in range(5))
    piece = Piece(PieceId("back"), "Wrap", points, outline, CutQuantity(1, 0, 0))
    style = Style(StyleId("w"), "Wrap", ("M",), "M", {"M": SizePieces.from_pieces((piece,))})
    joined = _topology(style, "join_edges", point_id="m").view("M")[0]
    assert [(str(s.start), str(s.end)) for s in joined.outline] == [("b", "c"), ("c", "d"), ("d", "a"), ("a", "b")]


def test_trim_moves_only_the_last_stretch_of_a_multi_point_line_and_an_outline_end():
    params = {"size": "M", "piece_id": "back", "line_id": "zig", "start": [2, 2], "end": [6, 6]}
    style = BUS.dispatch(_with_line(_style(), "cut", [10, 0], [10, 30]), History(), "add_line", params)[0]
    back = _back(style)
    zig = replace(back.internal_lines[-1], points=(Point2D(2, 2), Point2D(6, 6), Point2D(16, 6)))
    style = style.with_piece("M", replace(back, internal_lines=(*back.internal_lines[:-1], zig)))
    trimmed = _back(_run(style, "trim_line", target="zig", end="end", boundary="cut")).internal_lines[-1]
    assert trimmed.points == (Point2D(2, 2), Point2D(6, 6), Point2D(10, 6))
    edge = _back(_run(_with_line(_style(), "cut", [10, -5], [10, 5]), "trim_line", target="s1", end="end",
                      boundary="cut"))
    assert edge.point(PointId("b")).position == Point2D(10, 0)


def test_a_curve_meeting_an_arc_takes_the_arc_tangent():
    params = {"size": "M", "piece_id": "back", "segment_id": "s2", "start_handle": [5, 10], "end_handle": [3, -4]}
    smoothed = _back(_run(BUS.dispatch(_style(), History(), "curve_edge", params)[0], "smooth_point", point_id="c"))
    handle = smoothed.outline[1].end_handle
    positions = {p.id: p.position for p in smoothed.points}
    arc = smoothed.outline[2]
    leaving = end_tangents(resolve_segment(arc, positions), positions[arc.start], positions[arc.end])[0]
    assert handle.length == pytest.approx(5) and cross(unit(handle), leaving) == pytest.approx(0, abs=1e-6)
    assert handle.x * leaving.x + handle.y * leaving.y < 0
    flat = BUS.dispatch(_style(), History(), "curve_edge", {**params, "end_handle": [0, 0]})[0]
    with pytest.raises(ValueError, match="has no handle"):
        _run(flat, "smooth_point", point_id="c")


def test_mirroring_reflects_a_label_direction_about_the_axis():
    style = _style()
    back = _back(style)
    tilted = style.with_piece("M", replace(back, labels=(replace(back.labels[0], rotation_degrees=30),)))
    assert _back(_run(tilted, "mirror_piece", axis_start=[0, 0], axis_end=[1, 0])).labels[0].rotation_degrees == -30
    assert _back(_run(tilted, "mirror_piece", axis_start=[0, 0], axis_end=[0, 1])).labels[0].rotation_degrees == 150


def test_a_split_point_id_already_in_use_is_named():
    with pytest.raises(ValueError, match="Point id a is already used"):
        _topology(_style(), "split_edge", segment_id="s1", t=0.5, point_id="a", new_segment_id="sx")
