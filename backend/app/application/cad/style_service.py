"""Use cases for editing V6 styles (CAD-07): every edit is a Command, guarded before it is saved.

Order of one edit: load the style at a version, dispatch the command through the bus, let the guard refuse
invalid geometry (GEOMETRY_INVALID, 422), then save only if nobody else saved in between (STYLE_CONFLICT, 409).
Undo and redo restore states that were guarded when they were first saved, so they are not re-checked.
"""

from collections.abc import Mapping

from app.application.cad.bus import CommandBus
from app.application.cad.guard import Guard, default_guard
from app.application.cad.style_commands import style_registry
from app.application.cad.style_from_project import style_from_project
from app.application.cad.style_snapshot import StyleSnapshotter
from app.domain.pattern.ids import PieceId
from app.domain.pattern.style import Style
from app.ports.style_store import StyleRecord, StyleStore


class StyleService:
    def __init__(self, store: StyleStore, projects, guard: Guard | None = None) -> None:
        self.store = store
        self.projects = projects  # the V5 project repository (get by id)
        self.guard = guard or default_guard()
        self.bus: CommandBus[Style] = CommandBus(style_registry(), StyleSnapshotter())

    def create_from_project(self, project_id: str) -> StyleRecord:
        style = style_from_project(self.projects.get(project_id))
        self.guard.check(None, style)
        return self.store.add(style, project_id)

    def get(self, style_id: str) -> StyleRecord:
        return self.store.get(style_id)

    def run(self, style_id: str, piece_id: str, command: str, params: Mapping[str, object]) -> StyleRecord:
        if "piece_id" in params:
            raise ValueError("The piece comes from the URL; remove piece_id from the command parameters")
        record = self.store.get(style_id)
        if PieceId(piece_id) not in record.style.piece_ids:
            raise KeyError(f"Unknown piece {piece_id}")
        style, history = self.bus.dispatch(record.style, record.history, command, {**params, "piece_id": piece_id})
        self.guard.check(record.style, style)
        return self._saved(record, style, history)

    def undo(self, style_id: str) -> StyleRecord:
        record = self.store.get(style_id)
        return self._saved(record, *self.bus.undo(record.style, record.history))

    def redo(self, style_id: str) -> StyleRecord:
        record = self.store.get(style_id)
        return self._saved(record, *self.bus.redo(record.style, record.history))

    def _saved(self, record: StyleRecord, style: Style, history) -> StyleRecord:
        version = self.store.save(style, history, record.version)
        return StyleRecord(style, history, version, record.project_id)
