"""Imported geometry must satisfy the response DTOs it is later read through; otherwise every read would fail.

Strict: a string "0.5" must not be stored where the contract promises a number.
"""
from pydantic import ValidationError

from app.api.models.marker import Marker
from app.api.models.pattern import Pattern
from app.application.errors import ImportInvalid


def check_import_contract(body):
    try:
        for version in (body.pattern, *body.grades):
            Pattern.model_validate(version, strict=True)
    except ValidationError as exc:
        raise ImportInvalid("IMPORT_GEOMETRY_INVALID", "Imported patterns do not match the pattern contract") from exc
    if body.marker is None:
        return
    try:
        Marker.model_validate(body.marker, strict=True)
    except ValidationError as exc:
        raise ImportInvalid("IMPORT_MARKER_INVALID", "Imported marker does not match the marker contract") from exc
