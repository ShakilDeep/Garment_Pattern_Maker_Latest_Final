"""P1-09: every modify tool works with complete parameters and names a missing or unknown one."""

import pytest
from test_cad_style_bus import _style
from test_modify_split_join import _split
from test_modify_trim_extend import _with_line

from app.application.cad.style_commands import style_registry

TARGET = {"size": "M", "piece_id": "back"}


def _lines():
    return _with_line(_with_line(_with_line(_style(), "h", [2, 10], [8, 10]), "wall", [15, 0], [15, 30]),
                      "mid", [5, 0], [5, 30])


COMPLETE = {
    "move_piece": ({**TARGET, "dx": 1, "dy": -1}, _style),
    "rotate_piece": ({**TARGET, "angle_degrees": 15, "center": [10, 10]}, _style),
    "mirror_piece": ({**TARGET, "axis_start": [0, 0], "axis_end": [0, 1]}, _style),
    "split_edge": ({"piece_id": "back", "segment_id": "s1", "t": 0.5, "point_id": "q", "new_segment_id": "sx"},
                   _style),
    "join_edges": ({"piece_id": "back", "point_id": "q"}, lambda: _split("s1", 0.5)),
    "trim_line": ({**TARGET, "target": "h", "end": "end", "boundary": "mid"}, _lines),
    "extend_line": ({**TARGET, "target": "h", "end": "end", "boundary": "wall"}, _lines),
    "smooth_point": ({**TARGET, "point_id": "b"}, _style),
}


@pytest.mark.parametrize("tool", sorted(COMPLETE))
def test_complete_parameters_work_and_each_missing_one_is_named(tool):
    params, style = COMPLETE[tool]
    registry = style_registry()
    registry.create(tool, params).apply(style())
    for name in params:
        with pytest.raises(ValueError, match=f"missing parameter {name}"):
            registry.create(tool, {k: v for k, v in params.items() if k != name})
    with pytest.raises(ValueError, match="unknown parameter colour"):
        registry.create(tool, {**params, "colour": "red"})
