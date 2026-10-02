"""P1-06: the command history persists as JSON-ready data and is integrity-checked when loaded."""

import json

import pytest

from app.application.cad.history import History
from app.application.cad.history_codec import history_from_data, history_to_data
from app.application.cad.snapshot import chunk, digest


def _j(text):
    return json.dumps(text)


def _history():
    history = History().recorded((chunk(_j("h")), chunk(_j("a")))).recorded((chunk(_j("h")), chunk(_j("b"))))
    return history.undone((chunk(_j("h")), chunk(_j("c"))))[0]


def test_round_trip_through_json_is_exact_and_drops_the_undone_state():
    assert digest(_j("b")) in _history().blobs
    data = json.loads(json.dumps(history_to_data(_history())))
    assert digest(_j("b")) not in data["blobs"]
    assert history_from_data(data) == _history().collected()
    assert history_from_data(None) == History()


def _tampered(change):
    data = history_to_data(_history())
    change(data)
    return data


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(schema_version=9), "Unsupported command history schema version 9"),
        (lambda d: d["blobs"].update({digest(_j("a")): "not a"}), "does not match its digest"),
        (lambda d: d["blobs"].update({digest("{ }"): "{ }"}), "not canonical JSON"),
        (lambda d: d["blobs"].pop(digest(_j("a"))), "missing a stored chunk"),
        (lambda d: d.update(undo=[[digest(_j("h"))]] * 100), "more than 100 undo and redo steps"),
        (lambda d: d.update(undo=[[]]), "at least one chunk"),
        (lambda d: d["blobs"].update({digest(_j("z")): _j("z")}), "a chunk no step uses"),
        (lambda d: d.update(redo="x"), "must be lists of digest lists"),
        (lambda d: d.pop("blobs"), "missing field 'blobs'"),
    ],
)
def test_corrupt_history_is_refused(change, message):
    with pytest.raises(ValueError, match=message):
        history_from_data(_tampered(change))
