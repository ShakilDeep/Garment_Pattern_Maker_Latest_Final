from app.api.models.base import OpenModel


class RequirementItem(OpenModel):
    key: str
    name: str
    status: str
    blocking: bool
    why: str


class Requirements(OpenModel):
    ready: bool
    items: list[RequirementItem]
    blockers: list[RequirementItem]


class ReadinessReport(Requirements):
    target_operation: str
    warnings: list[RequirementItem]
    next_actions: list[str]


class RequirementQueue(OpenModel):
    items: list[RequirementItem]
    next: RequirementItem | None
    remaining: int
