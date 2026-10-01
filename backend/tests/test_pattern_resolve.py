"""P1-02: pattern segments resolve to the sampled domain/geom curves (absolute control points, arc centre)."""

from math import isclose

import pytest
from test_pattern_piece import P, _piece

from app.domain.geom.curves import Arc, CubicBezier
from app.domain.geom.primitives import LineSegment, Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.resolve import outline_curves
from app.domain.pattern.segment import Arc as PatternArc


def _close(a, b):
    return isclose(a.x, b.x, abs_tol=1e-9) and isclose(a.y, b.y, abs_tol=1e-9)


def test_outline_resolves_to_geom_curves_joined_end_to_end():
    curves = outline_curves(_piece())
    assert [type(c) for c in curves] == [LineSegment, CubicBezier, Arc, LineSegment]
    bezier = curves[1]
    assert (bezier.control1, bezier.control2) == (Point2D(25, 10), Point2D(25, 20))
    samples = [c.sample() if not isinstance(c, LineSegment) else (c.start, c.end) for c in curves]
    for current, following in zip(samples, (*samples[1:], samples[0])):
        assert _close(current[-1], following[0])


def test_arc_centre_and_radius_follow_the_bulge():
    arc = outline_curves(_piece())[2]  # c=(20,30) -> d=(0,30), bulge 0.4: radius = chord * (1 + b^2) / (4b)
    assert isinstance(arc, Arc) and isclose(arc.radius, 20 * 1.16 / 1.6)
    assert _close(arc.sample()[0], Point2D(20, 30)) and _close(arc.sample()[-1], Point2D(0, 30))


def test_bulge_one_is_a_half_circle_centred_on_the_chord():
    outline = (
        PatternArc(SegmentId("s1"), P["a"], P["c"], 1.0),
        PatternArc(SegmentId("s2"), P["c"], P["a"], 1.0),
    )
    arc = outline_curves(_piece(outline=outline, fold=None, cut=CutQuantity(1, 0, 0)))[0]
    assert _close(arc.center, Point2D(10, 15)) and isclose(arc.radius, 0.5 * (20**2 + 30**2) ** 0.5)


@pytest.mark.parametrize("bulge", [-0.4, 2.0, -3.0, 1e-6])
def test_bulge_sign_and_size_set_the_sagitta(bulge):
    """Chord (0,0)->(20,0): the arc midpoint sits bulge * chord / 2 below the chord for a positive bulge."""
    outline = (
        PatternArc(SegmentId("s1"), P["a"], P["b"], bulge),
        PatternArc(SegmentId("s2"), P["b"], P["a"], 1.0),
    )
    arc = outline_curves(_piece(outline=outline, fold=None, cut=CutQuantity(1, 0, 0)))[0]
    samples = arc.sample(steps=2)
    assert _close(samples[0], Point2D(0, 0)) and _close(samples[-1], Point2D(20, 0))
    assert isclose(samples[1].y, -bulge * 10, abs_tol=1e-6) and isclose(samples[1].x, 10, abs_tol=1e-6)
