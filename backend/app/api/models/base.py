from typing import Any

from pydantic import BaseModel, ConfigDict

Record = dict[str, Any]


class OpenModel(BaseModel):
    """Response DTO: declared fields are the typed contract; other snapshot fields pass through unchanged."""

    model_config = ConfigDict(extra="allow")
