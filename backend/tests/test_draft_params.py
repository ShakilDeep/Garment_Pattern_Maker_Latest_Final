"""P1-08: every draft tool refuses a missing or unknown parameter with a 400-class error naming it."""

import pytest
from test_cad_style_bus import _style
from test_draft_shapes import CIRCLE, RECTANGLE

from app.application.cad.style_commands import style_registry

TARGET = {"size": "M", "piece_id": "back"}
COMPLETE = {
    "add_point": {**TARGET, "point_id": "q", "x": 1, "y": 1},
    "add_line": {**TARGET, "line_id": "l", "start": [0, 1], "end": [1, 1]},
    "curve_edge": {**TARGET, "segment_id": "s1", "start_handle": [1, 0], "end_handle": [-1, 0]},
    "add_rectangle": RECTANGLE,
    "add_circle": CIRCLE,
    "offset_edge": {**TARGET, "segment_id": "s1", "distance": 1, "line_id": "o"},
    "parallel_line": {**TARGET, "segment_id": "s1", "through": [0, 4], "line_id": "p"},
    "perpendicular_line": {**TARGET, "segment_id": "s4", "start": [4, 4], "line_id": "n"},
    "intersection_point": {**TARGET, "first": "s1", "second": "s4", "point_id": "x"},
}


@pytest.mark.parametrize("tool", sorted(COMPLETE))
def test_complete_parameters_work_and_each_missing_one_is_named(tool):
    registry = style_registry()
    registry.create(tool, COMPLETE[tool]).apply(_style())
    for name in COMPLETE[tool]:
        with pytest.raises(ValueError, match=f"missing parameter {name}"):
            registry.create(tool, {k: v for k, v in COMPLETE[tool].items() if k != name})
    with pytest.raises(ValueError, match="unknown parameter colour"):
        registry.create(tool, {**COMPLETE[tool], "colour": "red"})
