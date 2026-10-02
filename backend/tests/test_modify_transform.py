"""P1-09 (CAD-02): move, rotate and mirror transform a whole piece, including every mark in absolute cm."""

import pytest
from test_cad_style_bus import BUS, _style
from test_draft_tools import _back

from app.application.cad.history import History
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.hashing import geometry_hash

ON_BACK = {"size": "M", "piece_id": "back"}


def _run(style, command, **params):
    return BUS.dispatch(style, History(), command, {**ON_BACK, **params})[0]


def test_move_shifts_points_and_marks_and_back_again_restores_the_hash():
    moved = _back(_run(_style(), "move_piece", dx=5, dy=-2))
    assert [p.position for p in moved.points][:2] == [Point2D(5, -2), Point2D(25, -2)]
    assert moved.grainline.start == Point2D(15, 3) and moved.labels[0].position == Point2D(15, 13)
    assert moved.outline == _back(_style()).outline and moved.notches == _back(_style()).notches
    back_again = _run(_run(_style(), "move_piece", dx=5, dy=-2), "move_piece", dx=-5, dy=2)
    assert geometry_hash(_back(back_again)) == geometry_hash(_back(_style()))


def test_rotate_turns_points_handles_and_label_direction():
    turned = _back(_run(_style(), "rotate_piece", angle_degrees=90, center=[0, 0]))
    assert turned.points[1].position == Point2D(0, 20)
    curve = turned.outline[1]
    assert (curve.start_handle, curve.end_handle) == (Vector2D(-10, 5), Vector2D(10, 5))
    assert turned.labels[0].rotation_degrees == 90 and turned.outline[2].bulge == 0.4


def test_mirror_flips_arcs_and_twice_restores_the_hash():
    flipped = _back(_run(_style(), "mirror_piece", axis_start=[0, 0], axis_end=[1, 0]))
    assert flipped.points[2].position == Point2D(20, -30) and flipped.outline[2].bulge == -0.4
    assert flipped.outline[1].start_handle == Vector2D(5, -10) and flipped.grainline.end == Point2D(10, -25)
    twice = _run(_run(_style(), "mirror_piece", axis_start=[0, 0], axis_end=[1, 0]), "mirror_piece",
                 axis_start=[0, 0], axis_end=[1, 0])
    assert geometry_hash(_back(twice)) == geometry_hash(_back(_style()))


@pytest.mark.parametrize(
    ("command", "params", "message"),
    [
        ("rotate_piece", {"angle_degrees": "90", "center": [0, 0]}, "finite number"),
        ("mirror_piece", {"axis_start": [1, 1], "axis_end": [1, 1]}, "two distinct points"),
        ("move_piece", {"dx": 1, "dy": float("nan")}, "finite number"),
    ],
)
def test_bad_transforms_are_refused(command, params, message):
    with pytest.raises(ValueError, match=message):
        _run(_style(), command, **params)
