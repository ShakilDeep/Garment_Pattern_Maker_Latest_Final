"""P1-08 (CAD-01): rectangle and circle draft new pieces in every size that has pieces (ungraded copies)."""

from itertools import pairwise
from math import pi

import pytest
from test_cad_guard import GUARD
from test_cad_style_bus import BUS, _style

from app.application.cad.history import History
from app.domain.pattern.edges import edge_polylines, orientation, stitch_ring
from app.domain.pattern.ids import PieceId
from app.domain.pattern.segment import Arc

RECTANGLE = {"piece_id": "pocket", "name": "Pocket", "x": 2, "y": 3, "width": 12, "height": 14, "quantity": 2}
CIRCLE = {"piece_id": "patch", "name": "Patch", "cx": 50, "cy": 50, "radius": 5, "quantity": 1}


def _length(piece):
    return sum(
        sum(((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 for a, b in pairwise(line))
        for line in edge_polylines(piece)
    )


def _drafted(command, params):
    before = _style()
    after = BUS.dispatch(before, History(), command, params)[0]
    GUARD.check(before, after)
    return after


def test_rectangle_adds_a_piece_to_every_sized_geometry():
    style = _drafted("add_rectangle", RECTANGLE)
    assert style.piece_ids[-1] == PieceId("pocket")
    for size in ("S", "M"):
        pocket = style.view(size)[-1]
        assert (pocket.name, pocket.cut.single, len(pocket.outline)) == ("Pocket", 2, 4)
        assert _length(pocket) == pytest.approx(52)
        corners = [(p.position.x, p.position.y) for p in pocket.points]
        assert corners == [(2, 3), (14, 3), (14, 17), (2, 17)] and orientation(stitch_ring(pocket)) == 1
    assert PieceId("pocket") not in style.allowances


def test_circle_is_two_semicircle_arcs():
    patch = _drafted("add_circle", CIRCLE).view("M")[-1]
    assert [type(s) for s in patch.outline] == [Arc, Arc] and {s.bulge for s in patch.outline} == {1.0}
    assert _length(patch) == pytest.approx(2 * pi * 5, abs=0.05)
    ring = stitch_ring(patch)
    assert orientation(ring) == 1 and max(p.y for p in ring) == pytest.approx(55)
    assert sum(p.x for p in ring) / len(ring) == pytest.approx(50) and min(p.x for p in ring) == 45


@pytest.mark.parametrize(
    ("command", "changes", "message"),
    [
        ("add_rectangle", {"width": 0}, "positive"),
        ("add_rectangle", {"piece_id": "back"}, "Duplicate piece id"),
        ("add_circle", {"radius": -1}, "positive"),
        ("add_circle", {"quantity": 0}, "whole number of at least 1"),
    ],
)
def test_bad_shapes_are_refused(command, changes, message):
    params = {**(RECTANGLE if command == "add_rectangle" else CIRCLE), **changes}
    with pytest.raises(ValueError, match=message):
        BUS.dispatch(_style(), History(), command, params)

