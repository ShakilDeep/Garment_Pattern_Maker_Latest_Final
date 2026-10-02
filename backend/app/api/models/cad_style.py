"""Typed DTOs for V6 styles and CAD command requests/results (P1-07)."""

from typing import Any

from pydantic import BaseModel, Field

from app.api.models.cad_piece import PieceView
from app.api.schemas import RequestModel
from app.ports.style_store import StyleRecord

ID_LENGTH = 64


class StyleCreate(RequestModel):
    project_id: str = Field(min_length=1, max_length=100)


class CadCommandRequest(RequestModel):
    command: str = Field(min_length=1, max_length=ID_LENGTH)
    params: dict[str, Any] = Field(default_factory=dict)


class StyleSummary(BaseModel):
    id: str
    name: str
    project_id: str | None
    sizes: list[str]
    base_size: str
    graded_sizes: list[str]  # sizes that have pieces; the others await grading
    piece_ids: list[str]
    version: int
    undo_steps: int
    redo_steps: int


class CommandResult(BaseModel):
    style: StyleSummary
    piece: PieceView


def style_summary(record: StyleRecord) -> StyleSummary:
    style, history = record.style, record.history
    return StyleSummary(
        id=str(style.id),
        name=style.name,
        project_id=record.project_id,
        sizes=list(style.sizes),
        base_size=style.base_size,
        graded_sizes=list(style.geometry),
        piece_ids=[str(piece) for piece in style.piece_ids],
        version=record.version,
        undo_steps=len(history.undo_steps),
        redo_steps=len(history.redo_steps),
    )
