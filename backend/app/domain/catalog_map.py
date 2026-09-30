"""Specification: catalog codes map only by exact source code, never by similarity."""
from app.domain.catalog import MAPPING


def map_code(code):
    if code in MAPPING:
        return MAPPING[code], "catalog", code
    return code, "unmapped", None
