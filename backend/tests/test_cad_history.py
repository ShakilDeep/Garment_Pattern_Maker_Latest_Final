"""P1-06 (PM-05): a content-addressed undo/redo history capped at 100 steps."""

import pytest

from app.application.cad.history import HISTORY_LIMIT, History
from app.application.cad.snapshot import chunk, digest
from app.application.errors import NotReady


def _state(n):
    return (chunk("header"), chunk(f"piece {n}"))


def test_undo_and_redo_walk_the_recorded_states():
    history = History().recorded(_state(0)).recorded(_state(1))
    history, restored = history.undone(_state(2))
    assert restored == _state(1)
    history, restored = history.undone(_state(1))
    assert restored == _state(0)
    history, restored = history.redone(_state(0))
    assert restored == _state(1)
    assert (len(history.undo_steps), len(history.redo_steps)) == (1, 1)


def test_a_new_step_clears_redo_and_drops_unreferenced_blobs():
    history, _ = History().recorded(_state(0)).undone(_state(1))
    history = history.recorded(_state(5))
    assert history.redo_steps == ()
    assert digest("piece 1") not in history.blobs and digest("piece 5") in history.blobs


def test_identical_chunks_are_stored_once():
    history = History().recorded(_state(0)).recorded(_state(1)).recorded(_state(0))
    assert sorted(history.blobs) == sorted(digest(t) for t in ("header", "piece 0", "piece 1"))


def test_history_keeps_the_last_100_steps():
    history = History()
    for n in range(HISTORY_LIMIT + 1):
        history = history.recorded(_state(n))
    assert HISTORY_LIMIT == 100 and len(history.undo_steps) == HISTORY_LIMIT
    assert digest("piece 0") not in history.blobs
    for n in reversed(range(1, HISTORY_LIMIT + 1)):
        history, restored = history.undone(_state(n + 1))
        assert restored == _state(n)
    with pytest.raises(NotReady, match="Nothing to undo"):
        history.undone(_state(1))


def test_empty_history_refuses_undo_and_redo():
    with pytest.raises(NotReady, match="Nothing to undo"):
        History().undone(_state(0))
    with pytest.raises(NotReady, match="Nothing to redo"):
        History().redone(_state(0))


def test_migrated_stacks_keep_the_newest_100_steps_in_total():
    history = History.from_states([_state(n) for n in range(80)], [_state(n) for n in range(80, 120)])
    assert (len(history.undo_steps), len(history.redo_steps)) == (80, 20)
    assert history.redone(_state(0))[1] == _state(119)
