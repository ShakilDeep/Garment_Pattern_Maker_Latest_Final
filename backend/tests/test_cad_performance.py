"""P1-06: on a 200-piece x 30-size style, edits after the first stay inside the 150 ms editor budget (doc 121).

The first edit splits every size into per-piece history chunks once (about 1.6 s on this style); later edits
reuse those chunks, so each stores and hashes only the piece it changed.
"""

from time import perf_counter

from test_style_performance import _document

from app.application.cad.bus import CommandBus
from app.application.cad.history import History
from app.application.cad.style_commands import style_registry
from app.application.cad.style_snapshot import StyleSnapshotter
from app.domain.pattern.style_codec import style_from_json

EDITS = 20
EDIT_BUDGET_SECONDS = 0.15


def _move(n):
    return {"size": "S0", "piece_id": "pc5", "point_id": "p0", "x": n, "y": 1}


def test_edits_and_undo_on_a_large_style_stay_within_the_editor_budget():
    bus = CommandBus(style_registry(), StyleSnapshotter())
    style, history = bus.dispatch(style_from_json(_document()), History(), "move_point", _move(0))
    slowest = 0.0
    for n in range(1, EDITS + 1):
        started = perf_counter()
        style, history = bus.dispatch(style, history, "move_point", _move(n))
        slowest = max(slowest, perf_counter() - started)
    started = perf_counter()
    style, history = bus.undo(style, history)
    undo_time = perf_counter() - started
    assert slowest < EDIT_BUDGET_SECONDS and undo_time < EDIT_BUDGET_SECONDS, (slowest, undo_time)
    assert style.view("S0")[5].point(style.view("S0")[5].points[0].id).position.x == EDITS - 1
