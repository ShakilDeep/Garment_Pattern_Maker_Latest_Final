"""A fresh id for every V6 style the application creates (from a block, a project or a project's copy)."""
from uuid import uuid4

from app.domain.pattern.ids import StyleId

STYLE_ID_HEX = 12


def new_style_id() -> StyleId:
    return StyleId(f"style-{uuid4().hex[:STYLE_ID_HEX]}")
