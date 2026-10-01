"""Page[T]: the envelope every GET collection endpoint returns."""
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
Offset = Annotated[int, Query(ge=0)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


def paginate[T](rows: list[T], limit: int, offset: int) -> dict[str, list[T] | int]:
    return {"items": rows[offset:offset + limit], "total": len(rows), "limit": limit, "offset": offset}
