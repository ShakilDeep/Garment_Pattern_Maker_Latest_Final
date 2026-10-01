from pydantic import Field

from app.api.models.base import OpenModel, Record


class MeasurementCell(OpenModel):
    value: float | None = None
    override: bool = False
    issue: str | None = None


class Measurement(OpenModel):
    key: str
    label: str
    code: str
    source: str | None = None
    tolerance: float | str | None = None
    values: dict[str, MeasurementCell] = Field(default_factory=dict)


class Document(OpenModel):
    id: str
    filename: str
    sha256: str
    bytes: int
    active: bool = True


class ParseStatus(OpenModel):
    project_id: str
    status: str
    documents: list[Document]
    measurements: int
    techpack: bool
    techpack_confidence: float | None = None
    issues: list[str]


class SourceComparison(OpenModel):
    documents: list[Document]
    same_content: bool
    active: list[Document]
    measurement_versions: list[Record]
    techpack_versions: list[Record]
