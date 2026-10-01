from app.api.models.base import OpenModel, Record
from app.api.models.marker import Marker
from app.api.models.pattern import Pattern
from app.api.models.project import Project


class ActionProposal(OpenModel):
    id: str
    intent: str
    target: str
    parameters: Record
    confidence: float
    requires_confirmation: bool
    status: str


class AssistantResult(OpenModel):
    project: Project
    validation: Record
    answer: str | None = None
    pattern: Pattern | None = None
    marker: Marker | None = None
