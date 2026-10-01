from pydantic import Field

from app.api.models.base import OpenModel, Record
from app.api.models.marker import Marker
from app.api.models.pattern import Pattern
from app.api.models.source import Document, Measurement


class ProjectSummary(OpenModel):
    id: str
    name: str
    updated_at: str | None = None
    archived: bool = False


class Project(ProjectSummary):
    state: str = "CREATED"
    measurements: list[Measurement] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    resolutions: Record = Field(default_factory=dict)
    techpack: Record | None = None
    pattern: Pattern | None = None
    pattern_history: list[Record] = Field(default_factory=list)
    grades: list[Pattern] = Field(default_factory=list)
    marker: Marker | None = None
    previous_marker: Marker | None = None
    audit: list[Record] = Field(default_factory=list)


class Deleted(OpenModel):
    deleted: bool


class GeometryImport(OpenModel):
    schema_version: int
    pattern: Pattern
    grades: list[Pattern]
    marker: Marker | None
