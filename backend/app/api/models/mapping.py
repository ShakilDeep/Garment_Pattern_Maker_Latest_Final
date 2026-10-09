from pydantic import BaseModel, Field, model_validator

from app.api.schemas import RequestModel


class MappingSuggestion(BaseModel):
    row: int
    key: str | None
    confidence: float
    provider: str
    reason: str


class StoredSuggestion(MappingSuggestion):
    at: str


class ChartRowView(BaseModel):
    row: int
    code: str
    label: str
    alt_label: str | None
    key: str
    status: str | None
    mapped_from: str | None
    half: bool
    tolerance: float | None
    base_value: float | None
    suggestion: StoredSuggestion | None


class ChartView(BaseModel):
    sizes: list[str]
    base_size: str | None
    value_size: str
    unit_hint: str | None
    canonical_keys: list[str]
    rows: list[ChartRowView]


class MappingChoice(RequestModel):
    """Exactly one of: a canonical key, or ``not_used: true``."""

    key: str | None = Field(default=None, min_length=1, max_length=64)
    not_used: bool = False

    @model_validator(mode="after")
    def one_choice(self):
        if (self.key is None) == (not self.not_used):
            raise ValueError("Choose a canonical key or mark the row not used")
        return self
