"""Port for persisting V6 styles with their command history (P1-07); SQLite now, PostgreSQL in P4."""

from dataclasses import dataclass
from typing import Protocol

from app.application.cad.history import History
from app.domain.pattern.style import Style


@dataclass(frozen=True)
class StyleRecord:
    style: Style
    history: History
    version: int  # increases by one on every save; a save names the version it was loaded at
    project_id: str | None = None


class StyleStore(Protocol):
    def add(self, style: Style, project_id: str | None) -> StyleRecord:
        """Store a new style at version 1; StyleConflict if its id is taken."""
        ...

    def get(self, style_id: str) -> StyleRecord:
        """KeyError if there is no such style."""
        ...

    def save(self, style: Style, history: History, expected_version: int) -> int:
        """Replace the style and history if it is still at `expected_version` (else StyleConflict)."""
        ...
