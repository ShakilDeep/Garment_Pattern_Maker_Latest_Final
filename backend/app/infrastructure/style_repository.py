"""SQLite adapter for the StyleStore port: one row per style, its JSON Memento and command history.

Saves are optimistic: a save names the version it was loaded at and fails with StyleConflict (409) when
another request saved first, so two concurrent edits can never silently overwrite each other.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.application.cad.history import History
from app.application.cad.history_codec import history_from_data, history_to_data
from app.application.errors import StyleConflict
from app.domain.pattern.style import Style
from app.domain.pattern.style_codec import style_from_json, style_to_json
from app.ports.style_store import StyleRecord

FIRST_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StyleRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(self, style: Style, project_id: str | None) -> StyleRecord:
        row = {"id": str(style.id), "name": style.name, "project_id": project_id, "version": FIRST_VERSION,
               "style": style_to_json(style), "history": json.dumps(history_to_data(History())), "at": _now()}
        try:
            with self.engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO styles (id, name, project_id, version, style_json, history_json, created_at,"
                    " updated_at) VALUES (:id, :name, :project_id, :version, :style, :history, :at, :at)"), row)
        except IntegrityError as exc:
            if self._exists(str(style.id)):
                raise StyleConflict(f"A style with id {style.id} already exists") from exc
            raise KeyError(f"Unknown project {project_id}") from exc  # the foreign key: the project is gone
        return StyleRecord(style, History(), FIRST_VERSION, project_id)

    def _exists(self, style_id: str) -> bool:
        with self.engine.connect() as connection:
            found = connection.execute(text("SELECT 1 FROM styles WHERE id = :id"), {"id": style_id}).first()
        return found is not None

    def get(self, style_id: str) -> StyleRecord:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT style_json, history_json, version, project_id FROM styles WHERE id = :id"),
                {"id": style_id},
            ).first()
        if row is None:
            raise KeyError(style_id)
        try:
            history = history_from_data(json.loads(row.history_json))
            return StyleRecord(style_from_json(row.style_json), history, row.version, row.project_id)
        except ValueError as exc:  # stored data the server wrote itself: corruption is a 500, not the client's error
            raise RuntimeError(f"Stored style {style_id} is corrupt") from exc

    def save(self, style: Style, history: History, expected_version: int) -> int:
        values = {"id": str(style.id), "name": style.name, "style": style_to_json(style),
                  "history": json.dumps(history_to_data(history)), "expected": expected_version, "at": _now()}
        with self.engine.begin() as connection:
            updated = connection.execute(text(
                "UPDATE styles SET name = :name, style_json = :style, history_json = :history,"
                " version = version + 1, updated_at = :at WHERE id = :id AND version = :expected"), values)
        if updated.rowcount != 1 and not self._exists(str(style.id)):
            raise KeyError(f"Unknown style {style.id}")
        if updated.rowcount != 1:
            raise StyleConflict(f"Style {style.id} changed since it was loaded; reload it and try again")
        return expected_version + 1
