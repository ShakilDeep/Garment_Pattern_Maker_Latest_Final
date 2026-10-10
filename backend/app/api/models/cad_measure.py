"""Typed DTOs for drafting a style from a block, the measure tool and seam walking (T130, P1-11)."""
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas import RequestModel
from app.application.cad.measure_query import MeasureKind, Measurement, MeasureRequest
from app.application.cad.walk import Placement, WalkPart, WalkResult

NAME = 64
SizeField = Field(min_length=1, max_length=NAME)


class BlockStyleCreate(RequestModel):
    block_id: str = Field(min_length=1, max_length=NAME)


class MeasureBody(RequestModel):
    size: str = SizeField
    piece_id: str = Field(min_length=1, max_length=NAME)
    kind: MeasureKind
    points: list[str] = Field(default_factory=list, max_length=2)
    edges: list[str] = Field(default_factory=list, max_length=500)
    point: str | None = Field(default=None, min_length=1, max_length=NAME)
    outline: Literal["sew", "cut"] = "sew"

    def request(self) -> MeasureRequest:
        return MeasureRequest(self.kind, tuple(self.points), tuple(self.edges), self.point, self.outline)


class MeasureView(BaseModel):
    kind: MeasureKind
    value: float
    unit: Literal["cm", "deg", "cm2"]

    @classmethod
    def of(cls, measurement: Measurement) -> "MeasureView":
        return cls(kind=measurement.kind, value=measurement.value, unit=measurement.unit)


class WalkPartBody(RequestModel):
    piece_id: str = Field(min_length=1, max_length=NAME)
    points: list[str] = Field(min_length=1, max_length=500)

    def part(self) -> WalkPart:
        return WalkPart(self.piece_id, tuple(self.points))


class WalkBody(RequestModel):
    size: str = SizeField
    first: list[WalkPartBody] = Field(min_length=1, max_length=50)
    second: list[WalkPartBody] = Field(min_length=1, max_length=50)
    at_cm: float | None = Field(default=None, ge=0)


class PlacementView(BaseModel):
    piece_id: str
    segment: str
    t: float


def _placement(placement: Placement) -> PlacementView:
    return PlacementView(piece_id=placement.piece_id, segment=str(placement.segment), t=placement.t)


class WalkView(BaseModel):
    first_cm: float
    second_cm: float
    difference_cm: float  # first - second: the ease the first seam carries
    at: tuple[PlacementView, PlacementView] | None

    @classmethod
    def of(cls, result: WalkResult) -> "WalkView":
        at = None if result.at is None else (_placement(result.at[0]), _placement(result.at[1]))
        return cls(first_cm=result.first_cm, second_cm=result.second_cm, difference_cm=result.difference_cm, at=at)
