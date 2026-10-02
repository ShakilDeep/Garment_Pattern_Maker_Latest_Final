"""P1-06: commands are created by name from a registry; unknown names and parameters are refused."""

import pytest
from test_cad_style_bus import _style

from app.application.cad.registry import Registry
from app.application.cad.style_commands import style_registry
from app.domain.pattern.ids import PieceId, PointId


def test_registered_commands_are_created_by_name():
    command = style_registry().create(
        "move_point", {"size": "M", "piece_id": "back", "point_id": "a", "x": 1, "y": 2}
    )
    moved = command.apply(_style()).view("M")[0].point(PointId("a"))
    assert command.name == "move_point" and (moved.position.x, moved.position.y) == (1, 2)
    assert style_registry().names == ("move_point",)


def test_unknown_commands_and_duplicate_names_are_refused():
    with pytest.raises(ValueError, match="Unsupported CAD command"):
        style_registry().create("explode", {})
    registry = Registry()
    registry.register("noop", lambda params: None)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("noop", lambda params: None)


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"size": "M", "piece_id": "back", "point_id": "a", "x": 1}, "missing parameter y"),
        ({"size": "M", "piece_id": "back", "point_id": "a", "x": 1, "y": 2, "z": 3}, "unknown parameter z"),
        ({"size": "M", "piece_id": "back", "point_id": "a", "x": "1", "y": 2}, "finite numbers"),
    ],
)
def test_invalid_parameters_are_refused(params, message):
    with pytest.raises(ValueError, match=message):
        style_registry().create("move_point", params)


def test_unknown_targets_are_not_found():
    params = {"size": "M", "piece_id": "nope", "point_id": "a", "x": 1, "y": 2}
    with pytest.raises(KeyError):
        style_registry().create("move_point", params).apply(_style())
    assert PieceId("back") in _style().piece_ids
