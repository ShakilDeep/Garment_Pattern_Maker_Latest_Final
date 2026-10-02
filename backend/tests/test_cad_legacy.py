"""P1-06: the V5 commands run through the command bus with a persisted 100-step history."""

from copy import deepcopy

import pytest

from app.api.models.project import Project
from app.application.cad.history import HISTORY_LIMIT, History
from app.application.cad.snapshot import state_key
from app.application.commands import BUS, SNAPSHOT_KEYS, execute
from app.application.errors import NotReady
from app.application.service import Service
from app.infrastructure.repository import Repository


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    service = Service(Repository(f"sqlite:///{tmp_path_factory.mktemp('legacy')}/cad.db"))
    project = service.create("Legacy CAD", True)
    project["resolutions"] = {"units": "cm", "review": "confirmed", "profile": "demo_v1", "placket": "workbook"}
    service.generate(project, "L")
    return service, service.repo.get(project["id"])


def _key(state):
    return state_key(BUS.snapshots.chunks(state))


def test_v5_edits_keep_100_identical_undo_steps(generated):
    state = {key: deepcopy(generated[1][key]) for key in SNAPSHOT_KEYS}
    history, keys = History(), [_key(state)]
    for n in range(1, HISTORY_LIMIT + 2):
        state, history = BUS.dispatch(state, history, "allowance", {"value": n * 0.02, "piece_id": None})
        keys.append(_key(state))
    for expected in reversed(keys[1:-1]):
        state, history = BUS.undo(state, history)
        assert _key(state) == expected
    assert state["pattern"]["seam_allowance"] == pytest.approx(0.02)
    with pytest.raises(NotReady, match="Nothing to undo"):
        BUS.undo(state, history)


def test_history_is_persisted_and_survives_a_reload(generated):
    service, project = generated
    edited = execute(service, project, "allowance", value=1)
    assert "command_undo" not in edited and len(edited["command_history"]["undo"]) == 1
    undone = execute(service, service.repo.get(project["id"]), "undo")
    assert undone["pattern"]["seam_allowance"] == 0
    assert len(service.repo.get(project["id"])["command_history"]["redo"]) == 1


def test_v5_snapshot_lists_are_migrated_without_losing_steps(generated):
    service, project = generated
    edited = execute(service, project, "allowance", value=2)
    old_format = {key: value for key, value in edited.items() if key != "command_history"}
    old_format["command_undo"] = [{key: deepcopy(project[key]) for key in SNAPSHOT_KEYS}]
    old_format["command_redo"] = [{key: deepcopy(edited[key]) for key in SNAPSHOT_KEYS}]
    undone = execute(service, old_format, "undo")
    assert undone["pattern"]["seam_allowance"] == 0 and "command_undo" not in undone
    assert len(undone["command_history"]["redo"]) == 2


def test_fold_and_notch_edits_undo_to_identical_states(generated):
    state = {key: deepcopy(generated[1][key]) for key in SNAPSHOT_KEYS}
    back = next(p for p in state["pattern"]["pieces"] if p["name"] == "Back")
    toggled = {"value": 0 if back["cut_on_fold"] else 1, "piece_id": back["id"]}
    folded, history = BUS.dispatch(state, History(), "fold", toggled)
    notched, history = BUS.dispatch(folded, history, "notch", {"value": 0.37, "piece_id": back["id"]})
    assert len({_key(state), _key(folded), _key(notched)}) == 3
    restored, history = BUS.undo(notched, history)
    assert _key(restored) == _key(folded)
    restored, _ = BUS.undo(restored, history)
    assert restored == state and _key(restored) == _key(state)


@pytest.mark.parametrize(
    ("command", "value", "message"),
    [
        ("allowance", 99, "between 0 and 3 cm"),
        ("notch", 1, "fraction from 0 to below 1"),
        ("fold", 1, "Select a generated piece"),
        ("explode", None, "Unsupported CAD command"),
        ("redo", None, "Nothing to redo"),
    ],
)
def test_invalid_v5_commands_are_refused(generated, command, value, message):
    service, project = generated
    with pytest.raises(ValueError, match=message):
        execute(service, project, command, value=value, piece_id="missing")


def test_the_history_stays_on_the_server(generated):
    edited = execute(*generated, "allowance", value=1.5)
    assert "command_history" not in Project.model_validate(edited).model_dump(mode="json")
