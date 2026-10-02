"""Typed DTOs for a piece's cut quantity, marks and seam allowance (CAD editor responses)."""

from pydantic import BaseModel

XY = tuple[float, float]


class CutModel(BaseModel):
    single: int
    mirrored_pairs: int
    on_fold: int


class NotchModel(BaseModel):
    id: str
    segment: str
    t: float


class InternalLineModel(BaseModel):
    id: str
    points: list[XY]


class DrillModel(BaseModel):
    id: str
    at: XY
    diameter: float


class LabelModel(BaseModel):
    id: str
    text: str
    at: XY
    rotation: float


class SeamAllowanceModel(BaseModel):
    default_width: float
    edge_widths: list[tuple[str, float]]
    corner_styles: list[tuple[str, str]]
