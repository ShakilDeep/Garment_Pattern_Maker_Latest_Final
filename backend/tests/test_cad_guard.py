"""P1-07 (CAD-07): the guard validates every changed piece of a command result before it is saved."""

import pytest
from test_cad_style_bus import BUS, _style
from test_seam_regressions import polygon

from app.application.cad.guard import default_guard
from app.application.cad.history import History
from app.application.errors import GeometryInvalid
from app.domain.pattern.ids import StyleId
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style

GUARD = default_guard()


def _edited(style, command, params):
    return BUS.dispatch(style, History(), command, params)[0]


def test_a_valid_edit_passes():
    style = _style()
    GUARD.check(style, _edited(style, "move_point", {"size": "M", "piece_id": "back", "point_id": "a",
                                                     "x": 1, "y": -1}))


def test_a_self_intersecting_outline_is_refused_with_details():
    style = _style()
    crossed = _edited(style, "move_point", {"size": "M", "piece_id": "back", "point_id": "a", "x": 10, "y": 60})
    with pytest.raises(GeometryInvalid, match=r"back \(M\)") as caught:
        GUARD.check(style, crossed)
    assert caught.value.code == "GEOMETRY_INVALID"
    assert caught.value.details == [
        {"size": "M", "piece_id": "back", "message": caught.value.details[0]["message"]}
    ]
    assert "not a simple outline" in caught.value.details[0]["message"]


def test_a_seam_allowance_that_cannot_be_cut_is_refused():
    needle = polygon([(0, 0), (100, 0.04), (0, 0.08)])
    style = Style(StyleId("needle"), "Needle", ("M",), "M", {"M": SizePieces.from_pieces((needle,))})
    params = {"piece_id": str(needle.id), "default_width": 1, "edge_widths": {}, "corner_styles": {}}
    with_allowance = _edited(style, "set_seam_allowance", params)
    with pytest.raises(GeometryInvalid) as caught:
        GUARD.check(style, with_allowance)
    assert "needle" in caught.value.details[0]["message"]
    GUARD.check(style, style)


def test_only_pieces_the_command_changed_are_checked():
    crossed = _edited(_style(), "move_point", {"size": "M", "piece_id": "back", "point_id": "a", "x": 10, "y": 60})
    other = _edited(crossed, "move_point", {"size": "M", "piece_id": "front", "point_id": "a", "x": 1, "y": 1})
    GUARD.check(crossed, other)
    with pytest.raises(GeometryInvalid):
        GUARD.check(_style(), other)
