"""Load a project's command history, migrating V5's `command_undo`/`command_redo` snapshot lists once.

V5 kept up to 20 full snapshots per stack; they become chunked steps of the PM-05 history, so no step is lost.
"""

from app.application.cad.history import History
from app.application.cad.history_codec import history_from_data
from app.application.cad.legacy_snapshot import LegacySnapshotter

HISTORY_KEY = "command_history"
V5_STACKS = ("command_undo", "command_redo")


def load_history(project: dict) -> History:
    """The project's history; V5 stacks are removed from `project` and folded in when no V6 history exists."""
    undo, redo = (project.pop(key, None) or [] for key in V5_STACKS)
    if project.get(HISTORY_KEY) is not None or not (undo or redo):
        return history_from_data(project.get(HISTORY_KEY))
    snapshots = LegacySnapshotter()
    try:
        return History.from_states([snapshots.chunks(s) for s in undo], [snapshots.chunks(s) for s in redo])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("The stored V5 undo history is malformed") from exc
