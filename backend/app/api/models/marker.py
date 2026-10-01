from pydantic import Field

from app.api.models.base import OpenModel
from app.api.models.pattern import Polygon


class Placement(OpenModel):
    name: str
    x: float
    y: float
    points: Polygon
    size: str | None = None


class Marker(OpenModel):
    placements: list[Placement]
    width: float
    length: float
    gap: float
    utilization: float
    waste: float
    strategy: str
    size: str | None = None
    quantities: dict[str, int] = Field(default_factory=dict)
    pattern_ids: dict[str, str] = Field(default_factory=dict)


class MarkerComparison(OpenModel):
    current_width: float
    previous_width: float
    current_length: float
    previous_length: float
    current_utilization: float
    previous_utilization: float
    length_delta: float
    utilization_delta: float
    piece_count_delta: int
    same_width: bool
    same_quantities: bool
