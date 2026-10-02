"""P1-07: a style stores each piece's seam allowance (PM-03), persists it and restores it on undo."""

import json

import pytest
from test_cad_style_bus import BUS, _style

from app.application.cad.history import History
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.style_codec import style_from_json, style_to_json

ALLOWANCE = SeamAllowance(1.5, ((SegmentId("s1"), 2.0),), ((PointId("b"), "square"),))
PARAMS = {"piece_id": "back", "default_width": 1.5, "edge_widths": {"s1": 2}, "corner_styles": {"b": "square"}}


def test_allowances_round_trip_and_documents_without_them_keep_their_text():
    plain = _style()
    assert "allowances" not in style_to_json(plain)
    styled = plain.with_allowance(PieceId("back"), ALLOWANCE)
    restored = style_from_json(style_to_json(styled))
    assert restored.allowances == {PieceId("back"): ALLOWANCE} and restored == styled


def test_set_seam_allowance_is_a_command_that_undo_reverts():
    style, history = BUS.dispatch(_style(), History(), "set_seam_allowance", PARAMS)
    assert style.allowances[PieceId("back")] == ALLOWANCE
    undone, _ = BUS.undo(style, history)
    assert undone.allowances == {} and undone == _style()


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"default_width": -1}, ValueError, "non-negative"),
        ({"corner_styles": {"b": "round"}}, ValueError, "Unknown corner style"),
        ({"edge_widths": [["s1", 2]]}, ValueError, "must be an object"),
        ({"piece_id": "nope"}, KeyError, "nope"),
    ],
)
def test_invalid_allowances_are_refused(changes, error, message):
    with pytest.raises(error, match=message):
        BUS.dispatch(_style(), History(), "set_seam_allowance", {**PARAMS, **changes})


def test_allowances_must_belong_to_the_style_and_be_well_formed():
    with pytest.raises(ValueError, match="unknown piece nope"):
        _style().__class__(**{**_style().__dict__, "allowances": {PieceId("nope"): ALLOWANCE}})
    document = json.loads(style_to_json(_style()))
    document["allowances"] = {"back": {"default_width": 1}}
    with pytest.raises(ValueError, match="missing field 'edge_widths'"):
        style_from_json(json.dumps(document))
