from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

Size = Literal["S", "M", "L", "XL", "XXL", "3XL"]
Quantity = Annotated[int, Field(strict=True, ge=1, le=20)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ObjectResponse(RootModel[dict[str, Any]]):
    """Stable JSON object contract for compatibility projections."""


class ListResponse(RootModel[list[Any]]):
    """Stable JSON list contract for compatibility projections."""


class ProjectCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    demo: bool = False


class Generate(RequestModel):
    size: Size = "L"
    allowance: float = Field(default=0, ge=0, le=3)


class Grade(RequestModel):
    sizes: list[Size] = Field(min_length=1, max_length=6)


class Nest(RequestModel):
    width: float = Field(gt=20, le=500)
    quantity: Quantity = 1
    gap: float = Field(default=0.5, ge=0.1, le=5)
    size: Size = "L"
    quantities: dict[Size, Quantity] | None = Field(default=None, min_length=1, max_length=6)
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    time_budget_ms: int = Field(default=250, ge=1, le=10_000)
    iterations: int = Field(default=1, ge=1, le=10_000)
    grain_policy: Literal['vertical'] = 'vertical'

    @model_validator(mode="after")
    def check_total(self):
        if self.quantities is not None and sum(self.quantities.values()) > 20:
            raise ValueError("Choose at most 20 garments in total")
        if self.quantities is not None and {"size", "quantity"} & self.model_fields_set:
            raise ValueError("Use quantities or size/quantity, not both")
        return self


class Resolve(RequestModel):
    value: str = Field(max_length=100)
    note: str = Field(default='', max_length=2000)
    actor: str = Field(default='local user', min_length=1, max_length=120)
    source_id: str | None = Field(default=None, max_length=100)
    resolution_type: Literal['manual', 'source', 'approved_default', 'not_applicable'] = 'manual'


class ExportCreate(RequestModel):
    kind: Literal['svg', 'pdf', 'json', 'marker-svg', 'marker-pdf']
    size: Size | None = None


class JsonImport(RequestModel):
    """Accept exported JSON; ignore provenance extras such as audit (Pydantic extra=ignore)."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    schema_version: Literal[1]
    project: str = Field(min_length=1, max_length=120)
    pattern: dict
    grades: list[dict] = Field(default_factory=list, max_length=6)
    marker: dict | None = None


class Measurements(RequestModel):
    size: Size
    changes: dict[str, float] = Field(max_length=100)


class Rename(RequestModel):
    name: str = Field(min_length=1, max_length=120)


class ReadinessCheck(RequestModel):
    target_operation: Literal['generate', 'grade', 'validate', 'marker', 'export']
    size: Size = 'L'
    width: float | None = None
    quantities: dict[Size, Quantity] | None = None
    grain_policy: Literal['vertical'] | None = None
