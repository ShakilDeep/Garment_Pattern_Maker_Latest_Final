"""P1-09 (CAD-02): smoothing a point makes the outline's tangent continuous there (G1), keeping handle lengths."""

import pytest
from test_cad_style_bus import _style
from test_draft_tools import _back
from test_modify_transform import _run

from app.domain.geom.lines import cross, unit
from app.domain.geom.primitives import Vector2D


def _curve_at_c(style):
    """Make s3 a cubic too, so the point c joins two curves."""
    return _run(style, "curve_edge", segment_id="s3", start_handle=[-2, 6], end_handle=[4, 3])


def test_a_curve_meeting_a_line_takes_the_line_direction():
    smoothed = _back(_run(_style(), "smooth_point", point_id="b")).outline[1]
    assert smoothed.start_handle.x == pytest.approx(Vector2D(5, 10).length) and smoothed.start_handle.y == 0
    assert smoothed.end_handle == _back(_style()).outline[1].end_handle


def test_two_curves_share_the_bisector_and_keep_their_lengths():
    before = _back(_curve_at_c(_style())).outline
    after = _back(_run(_curve_at_c(_style()), "smooth_point", point_id="c")).outline
    incoming, outgoing = after[1].end_handle, after[2].start_handle
    assert cross(unit(incoming), unit(outgoing)) == pytest.approx(0, abs=1e-6)
    assert incoming.x * outgoing.x + incoming.y * outgoing.y < 0
    assert incoming.length == pytest.approx(before[1].end_handle.length)
    assert outgoing.length == pytest.approx(before[2].start_handle.length)


def test_a_corner_between_two_straight_edges_cannot_be_smoothed():
    with pytest.raises(ValueError, match="needs a curve"):
        _run(_style(), "smooth_point", point_id="a")
    with pytest.raises(KeyError):
        _run(_style(), "smooth_point", point_id="nope")
