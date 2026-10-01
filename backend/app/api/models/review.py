from app.api.models.base import OpenModel


class ReviewGate(OpenModel):
    gate: str
    status: str
    note: str = ""
    actor: str | None = None
    at: str | None = None
