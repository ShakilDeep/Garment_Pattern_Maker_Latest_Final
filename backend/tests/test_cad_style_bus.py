"""P1-06 acceptance (PM-05): every style edit is a Command; 100 undos restore identical geometry hashes."""

from dataclasses import replace

import pytest
from test_pattern_piece import _piece

from app.application.cad.bus import CommandBus
from app.application.cad.history import HISTORY_LIMIT, History
from app.application.cad.snapshot import chunk, state_key
from app.application.cad.style_commands import style_registry
from app.application.cad.style_snapshot import StyleSnapshotter
from app.application.errors import NotReady
from app.domain.pattern.hashing import geometry_hash
from app.domain.pattern.ids import PieceId, StyleId
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style
from app.domain.pattern.style_codec import style_from_json, style_to_json

SNAPSHOTS = StyleSnapshotter()
BUS = CommandBus(style_registry(), SNAPSHOTS)


def _style():
    pieces = SizePieces.from_pieces((_piece(), replace(_piece(), id=PieceId("front"), name="Front")))
    return Style(StyleId("shirt"), "Shirt", ("S", "M"), "M", {"S": pieces, "M": pieces})


def _move(n):
    return {"size": "M", "piece_id": "back", "point_id": "a", "x": n * 0.1, "y": -n * 0.05}


def _fingerprint(style):
    hashes = tuple(geometry_hash(p) for size in style.geometry for p in style.view(size))
    return state_key(SNAPSHOTS.chunks(style)), hashes


@pytest.mark.parametrize("loaded", [False, True])
def test_100_undos_and_redos_restore_identical_hashes(loaded):
    style, history = (style_from_json(style_to_json(_style())) if loaded else _style()), History()
    seen = [_fingerprint(style)]
    for n in range(1, HISTORY_LIMIT + 1):
        style, history = BUS.dispatch(style, history, "move_point", _move(n))
        seen.append(_fingerprint(style))
    assert len(set(seen)) == HISTORY_LIMIT + 1
    for expected in reversed(seen[:-1]):
        style, history = BUS.undo(style, history)
        assert _fingerprint(style) == expected
    assert style == _style()
    for expected in seen[1:]:
        style, history = BUS.redo(style, history)
        assert _fingerprint(style) == expected


def test_the_oldest_step_is_dropped_after_100():
    style, history = _style(), History()
    for n in range(1, HISTORY_LIMIT + 2):
        style, history = BUS.dispatch(style, history, "move_point", _move(n))
    for _ in range(HISTORY_LIMIT):
        style, history = BUS.undo(style, history)
    assert style.view("M")[0].point(_piece().points[0].id).position.x == pytest.approx(0.1)
    with pytest.raises(NotReady, match="Nothing to undo"):
        BUS.undo(style, history)


def test_undo_reuses_sizes_the_command_did_not_touch():
    style, history = BUS.dispatch(_style(), History(), "move_point", _move(1))
    restored, _ = BUS.undo(style, history)
    assert restored.geometry["S"] is style.geometry["S"]
    assert restored.geometry["M"] == _style().geometry["M"]


def test_a_failed_command_changes_nothing():
    style, history = BUS.dispatch(_style(), History(), "move_point", _move(1))
    with pytest.raises(KeyError):
        BUS.dispatch(style, history, "move_point", {**_move(2), "point_id": "nope"})
    assert BUS.undo(style, history)[0] == _style()


def test_a_history_of_the_wrong_shape_is_refused():
    wrong = History(undo_steps=((chunk("not json")[0],),), blobs=dict([chunk("not json")]))
    with pytest.raises(ValueError, match="history is malformed"):
        BUS.undo(_style(), wrong)
