"""Accuracy report response (T143): one row per check per size, a status header and the From-block list."""
from typing import Literal

from pydantic import Field

from app.api.models.base import OpenModel


class LimitSource(OpenModel):
    kind: Literal["chart", "pds", "setting"]
    ref: str


class AccuracyCheck(OpenModel):
    name: str
    value: float
    limit: str
    passed: bool
    gate: bool
    source: LimitSource
    size: str | None = None
    piece: str | None = None
    edge: str | None = None


class FromBlockInput(OpenModel):
    input: str
    sizes: list[str]


class AccuracyReport(OpenModel):
    profile: str
    reference: str | None = None
    status: Literal["ready", "errors", "no_reference"]
    error_count: int
    sizes_checked: list[str] = Field(default_factory=list)
    sizes_not_drafted: list[str] = Field(default_factory=list)
    checks: list[AccuracyCheck] = Field(default_factory=list)
    from_block: list[FromBlockInput] = Field(default_factory=list)
    optitex: str
