"""T129: fit one cubic Bézier through a sampled run (end points fixed), to read curve shapes off the PDS."""
from math import hypot

import pytest

from app.domain.geom.bezier_fit import fit_cubic
from app.domain.geom.curves import CubicBezier
from app.domain.geom.primitives import Point2D, Vector2D
from app.infrastructure.aama.corners import split_vertices

KNOWN = CubicBezier(Point2D(0, 0), Point2D(3, 6), Point2D(9, 7), Point2D(12, 1))
FRONT_ARMHOLE = ((52.92, -1.83), (72.51, -8.3))  # FRT L sew line: underarm to shoulder point (rounded)


def _deviation(points: list[Point2D], start: Point2D, handles: tuple[Vector2D, Vector2D]) -> float:
    end = points[-1]
    curve = CubicBezier(start, Point2D(start.x + handles[0].x, start.y + handles[0].y),
                        Point2D(end.x + handles[1].x, end.y + handles[1].y), end)
    dense = curve.sample(4000)
    return max(min(hypot(p.x - q.x, p.y - q.y) for q in dense) for p in points)


def test_a_sampled_cubic_is_recovered():
    fit = fit_cubic(KNOWN.sample(40))
    assert (fit.start_handle.x, fit.start_handle.y) == pytest.approx((3, 6), abs=1e-3)
    assert (fit.end_handle.x, fit.end_handle.y) == pytest.approx((-3, 6), abs=1e-3)
    assert fit.max_deviation < 1e-4


def test_a_straight_run_gives_handles_along_the_chord():
    fit = fit_cubic([Point2D(0, 0), Point2D(2, 1), Point2D(4, 2), Point2D(10, 5)])
    assert fit.start_handle.x * 5 - fit.start_handle.y * 10 == pytest.approx(0, abs=1e-9)
    assert fit.end_handle.x * 5 - fit.end_handle.y * 10 == pytest.approx(0, abs=1e-9)
    assert fit.max_deviation == pytest.approx(0, abs=1e-9)


def test_two_points_are_a_straight_curve_with_third_handles():
    fit = fit_cubic([Point2D(0, 0), Point2D(9, 3)])
    assert (fit.start_handle, fit.end_handle, fit.max_deviation) == (Vector2D(3, 1), Vector2D(-3, -1), 0)


@pytest.mark.parametrize("points", [[], [Point2D(1, 1)], [Point2D(1, 1), Point2D(1, 1)]])
def test_a_run_needs_two_distinct_end_points(points):
    with pytest.raises(ValueError, match="A curve fit needs two distinct end points"):
        fit_cubic(points)


def test_the_pds_front_armhole_fits_and_reports_its_true_deviation(pds_styles):
    ring = pds_styles["1078375"].pieces[0].outline.sew[0]
    turns, _ = split_vertices(ring)
    start, end = (min(turns, key=lambda t, at=at: hypot(t[0] - at[0], t[1] - at[1])) for at in FRONT_ARMHOLE)
    run = [Point2D(*p) for p in ring[ring.index(start):ring.index(end) + 1]]
    fit = fit_cubic(run)
    assert len(run) == 16
    assert fit.max_deviation == pytest.approx(_deviation(run, run[0], (fit.start_handle, fit.end_handle)), abs=2e-3)
    assert fit.max_deviation < 0.05


def test_a_sparse_run_never_fits_a_looping_curve(pds_styles):
    ring = list(pds_styles["1078375"].pieces[2].outline.sew[0])  # back YK: armhole, 5 PDS samples
    start, end = ring.index((73.03, -56.66)), ring.index((85.6, -54.7))
    run = [Point2D(*p) for p in ring[start:end + 1]]
    fit = fit_cubic(run)
    chord = Vector2D.between(run[0], run[-1])
    assert len(run) == 5
    assert fit.start_handle.x * chord.x + fit.start_handle.y * chord.y > 0
    assert fit.end_handle.x * chord.x + fit.end_handle.y * chord.y < 0
    assert fit.max_deviation < 0.1  # the agreed curve tolerance (docs/drafting/shirt.md Q4)
