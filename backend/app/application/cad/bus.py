"""Command bus (PM-05): create a command by name, apply it, and record the previous state for undo.

A failed command raises before anything is recorded, so the caller's state and history stay as they were.
The previous state is chunked before the command runs, so its key does not depend on what the command reads.
"""

import json

from app.application.cad.command import Params
from app.application.cad.history import History
from app.application.cad.registry import Registry
from app.application.cad.snapshot import Chunks, Snapshotter


class CommandBus[State]:
    def __init__(self, registry: Registry[State], snapshots: Snapshotter[State]) -> None:
        self.registry = registry
        self.snapshots = snapshots

    def dispatch(self, state: State, history: History, name: str, params: Params) -> tuple[State, History]:
        command = self.registry.create(name, params)
        before = self.snapshots.chunks(state)
        return command.apply(state), history.recorded(before)

    def undo(self, state: State, history: History) -> tuple[State, History]:
        history, chunks = history.undone(self.snapshots.chunks(state))
        return self._restored(chunks, state), history

    def redo(self, state: State, history: History) -> tuple[State, History]:
        history, chunks = history.redone(self.snapshots.chunks(state))
        return self._restored(chunks, state), history

    def _restored(self, chunks: Chunks, current: State) -> State:
        """Chunks pass their digest check, but a crafted history can still hold the wrong shape: refuse it (400)."""
        try:
            return self.snapshots.restore(chunks, current)
        except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise ValueError("The stored command history is malformed") from exc
