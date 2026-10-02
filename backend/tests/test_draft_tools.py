"""P1-08 (CAD-01): draft tools for points, lines and curves are Commands on one piece of one size."""

import pytest
from test_cad_style_bus import BUS, _style

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.segment import CubicBezier

ON_BACK = {"size": "M", "piece_id": "back"}


def _run(command, **params):
    return BUS.dispatch(_style(), History(), command, {**ON_BACK, **params})[0]


def _back(style, size="M"):
    return style.view(size)[0]


def test_point_adds_a_construction_point():
    back = _back(_run("add_point", point_id="q1", x=5, y=6.5))
    assert back.point(PointId("q1")).position == Point2D(5, 6.5)
    assert _back(_style(), "S") == _back(_run("add_point", point_id="q1", x=5, y=6.5), "S")
    with pytest.raises(ValueError, match="Duplicate"):
        _run("add_point", point_id="a", x=1, y=1)


def test_line_adds_an_internal_line():
    back = _back(_run("add_line", line_id="L2", start=[0, 10], end=[20, 10]))
    assert back.internal_lines[-1].points == (Point2D(0, 10), Point2D(20, 10))
    with pytest.raises(ValueError, match="two distinct points"):
        _run("add_line", line_id="L2", start=[3, 3], end=[3, 3])
    with pytest.raises(ValueError, match=r"\[x, y\]"):
        _run("add_line", line_id="L2", start=[3], end=[3, 3])


def test_curve_turns_an_edge_into_a_bezier_and_keeps_its_id_and_notches():
    back = _back(_run("curve_edge", segment_id="s1", start_handle=[5, -4], end_handle=[-5, -4]))
    curved = next(s for s in back.outline if s.id == SegmentId("s1"))
    assert isinstance(curved, CubicBezier)
    assert (curved.start_handle, curved.end_handle) == (Vector2D(5, -4), Vector2D(-5, -4))
    assert back.notches == _back(_style()).notches
    with pytest.raises(KeyError):
        _run("curve_edge", segment_id="nope", start_handle=[1, 1], end_handle=[1, 1])
