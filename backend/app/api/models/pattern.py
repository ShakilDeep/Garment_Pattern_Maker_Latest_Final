from pydantic import Field

from app.api.models.base import OpenModel

Polygon = list[list[float]]


class Issue(OpenModel):
    severity: str
    code: str | None = None
    message: str | None = None


class Piece(OpenModel):
    id: str
    name: str
    points: Polygon


class Pattern(OpenModel):
    id: str
    size: str
    pieces: list[Piece]
    validation: list[Issue] = Field(default_factory=list)
    profile: str | None = None
    input_hash: str | None = None
    seam_allowance: float | None = None
    stale: bool = False
    graded_from: str | None = None
