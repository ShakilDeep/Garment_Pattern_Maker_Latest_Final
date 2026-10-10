"""T130: naming PDS sew-line vertices after recipe points: orientation, notch feet, snapping and runs."""
import pytest

from app.domain.reference import PieceOutline, ReferencePiece
from app.infrastructure.pds.named_points import ccw_ring, foot, run, snap, with_foot

CLOCKWISE = ((0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (10.0, 0.0), (0.0, 0.0))


def _piece(sew) -> ReferencePiece:
    return ReferencePiece("P", "", 1, False, 0.0, "", {}, PieceOutline(cut=(sew,), sew=(sew,)))


def test_the_ring_is_open_counter_clockwise_and_without_repeated_vertices():
    assert ccw_ring(_piece(CLOCKWISE)) == [(10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]


def test_a_notch_foot_is_inserted_once_on_its_nearest_segment():
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert foot(ring, (4.0, -0.3)) == (0, (4.0, 0.0))
    placed = with_foot(ring, (4.0, -0.3))
    assert placed == [(0.0, 0.0), (4.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert with_foot(placed, (4.0, 0.2)) == placed


def test_snap_names_only_a_vertex_within_half_a_millimetre():
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    assert snap(ring, "SP", (10.03, 0.02)) == 1
    with pytest.raises(ValueError, match="No PDS sew-line vertex for SP near"):
        snap(ring, "SP", (10.1, 0.0))


def test_a_run_wraps_around_the_ring():
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert run(ring, 2, 0) == [(10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    assert run(ring, 0, 1) == [(0.0, 0.0), (10.0, 0.0)]


def test_a_ring_of_one_point_has_no_segment():
    with pytest.raises(ValueError, match="A PDS sew line needs at least two points"):
        foot([], (0.0, 0.0))
