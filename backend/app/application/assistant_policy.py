"""Parameter schemas and application-owned assistant dispatch policy."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.catalog import MAPPING

Size = Literal["S", "M", "L", "XL", "XXL", "3XL"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Explanation(StrictModel):
    answer: str = Field(min_length=1, max_length=4000)


class Adjustment(StrictModel):
    measurement: str
    delta: float = Field(ge=-500, le=500)
    size: Size

    @model_validator(mode="after")
    def canonical_key(self):
        if self.measurement not in MAPPING.values():
            raise ValueError("Unknown canonical measurement")
        return self


class Allowance(StrictModel):
    value: float = Field(ge=0, le=3)


class Generation(StrictModel):
    size: Size


class Marker(Generation):
    width: float = Field(gt=20, le=500)
    quantity: int = Field(ge=1, le=20)
    gap: float = Field(ge=0.1, le=5)


class LabelMapping(StrictModel):
    source_label: str = Field(min_length=1, max_length=100)
    canonical_key: str

    @model_validator(mode="after")
    def known_key(self):
        if self.canonical_key not in MAPPING.values():
            raise ValueError("Unknown canonical measurement")
        return self


POLICY: dict[str, tuple[type[StrictModel], str | None, str, bool]] = {
    "explain": (Explanation, "project", "none", False),
    "adjust_measurement": (Adjustment, None, "measurements", True),
    "set_allowance": (Allowance, "pattern", "cad_commands", True),
    "generate_pattern": (Generation, "pattern", "pattern_generation", True),
    "optimize_marker": (Marker, "marker", "marker", True),
    "accept_mapping": (LabelMapping, "project", "requirements", True),
}
