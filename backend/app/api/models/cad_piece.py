"""Typed piece DTO for the CAD editor (CAD-07): the piece Memento plus its cut outline, never a free dict."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.api.models.cad_marks import (
    XY,
    CutModel,
    DrillModel,
    InternalLineModel,
    LabelModel,
    NotchModel,
    SeamAllowanceModel,
)
from app.application.cad.piece_detail import PieceDetail
from app.domain.pattern.seam_codec import allowance_to_data
from app.domain.pattern.serialize import piece_to_data


class PointModel(BaseModel):
    id: str
    x: float
    y: float
    grade_rule: str | None


class _Ends(BaseModel):
    id: str
    start: str
    end: str


class LineSegment(_Ends):
    type: Literal["line"]


class CubicSegment(_Ends):
    type: Literal["cubic"]
    start_handle: XY  # offset from `start`, in cm
    end_handle: XY  # offset from `end`, in cm


class ArcSegment(_Ends):
    type: Literal["arc"]
    bulge: float  # tan(θ/4); its sign gives the direction


Segment = Annotated[LineSegment | CubicSegment | ArcSegment, Field(discriminator="type")]


class PieceView(BaseModel):
    style_id: str
    size: str
    id: str
    name: str
    points: list[PointModel]
    outline: list[Segment]
    cut: CutModel
    grainline: tuple[XY, XY] | None
    fold: str | None
    internal_lines: list[InternalLineModel]
    notches: list[NotchModel]
    drills: list[DrillModel]
    labels: list[LabelModel]
    geometry_hash: str
    seam_allowance: SeamAllowanceModel | None
    cut_outline: list[XY] | None  # None while the piece has no seam allowance


def piece_view(detail: PieceDetail) -> PieceView:
    data = {key: value for key, value in piece_to_data(detail.piece).items() if key != "schema_version"}
    allowance = None if detail.allowance is None else allowance_to_data(detail.allowance)
    cut = None if detail.cut_outline is None else [(p.x, p.y) for p in detail.cut_outline]
    extra = {"style_id": detail.style_id, "size": detail.size, "geometry_hash": detail.geometry_hash}
    return PieceView.model_validate({**data, **extra, "seam_allowance": allowance, "cut_outline": cut})
