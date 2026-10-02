"""V6 style and CAD command routes (CAD-07): the editor sends Commands; geometry is decided here, not in the UI.

Piece ids are unique only within a style, so pieces are addressed as /styles/{style_id}/pieces/{piece_id}.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.models.cad_piece import PieceView, piece_view
from app.api.models.cad_style import (
    CadCommandRequest,
    CommandResult,
    StyleCreate,
    StyleSummary,
    style_summary,
)
from app.application.cad.piece_detail import piece_detail
from app.application.cad.style_service import StyleService
from app.ports.style_store import StyleRecord

SizeLabel = Annotated[str, Query(min_length=1, max_length=64)]


def _result_size(record: StyleRecord, params: dict) -> str:
    """The size the command edited, or the base size for style-wide commands such as a seam allowance."""
    size = params.get("size")
    return size if isinstance(size, str) and size in record.style.geometry else record.style.base_size


def cad_routes(styles: StyleService):
    routes = APIRouter(prefix="/styles")

    @routes.post("", response_model=StyleSummary)
    def create(body: StyleCreate):
        return style_summary(styles.create_from_project(body.project_id))

    @routes.get("/{style_id}", response_model=StyleSummary)
    def get(style_id: str):
        return style_summary(styles.get(style_id))

    @routes.get("/{style_id}/pieces/{piece_id}", response_model=PieceView)
    def piece(style_id: str, piece_id: str, size: SizeLabel):
        return piece_view(piece_detail(styles.get(style_id).style, piece_id, size))

    @routes.post("/{style_id}/pieces/{piece_id}/commands", response_model=CommandResult)
    def command(style_id: str, piece_id: str, body: CadCommandRequest):
        record = styles.run(style_id, piece_id, body.command, body.params)
        detail = piece_detail(record.style, piece_id, _result_size(record, body.params))
        return CommandResult(style=style_summary(record), piece=piece_view(detail))

    @routes.post("/{style_id}/undo", response_model=StyleSummary)
    def undo(style_id: str):
        return style_summary(styles.undo(style_id))

    @routes.post("/{style_id}/redo", response_model=StyleSummary)
    def redo(style_id: str):
        return style_summary(styles.redo(style_id))

    return routes
