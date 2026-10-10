"""DTOs for style detection (T132): the option table, a stored proposal and the user's confirmation."""
from pydantic import BaseModel, Field

from app.api.schemas import RequestModel


class OptionSpecOut(BaseModel):
    id: str
    label: str
    families: list[str]
    choices: list[str]
    note: str


class OptionGuessOut(BaseModel):
    id: str
    value: str
    confidence: float


class StyleProposalOut(BaseModel):
    garment: OptionGuessOut
    fit: OptionGuessOut
    options: list[OptionGuessOut]
    provider: str
    model: str
    prompt_version: str


class StyleDetection(BaseModel):
    proposal: StyleProposalOut
    source_sha256: str
    page: int
    at: str


class StyleChoicesIn(RequestModel):
    garment: str = Field(max_length=40)
    fit: str = Field(max_length=40)
    options: dict[str, str] = Field(max_length=20)
