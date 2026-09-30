"""Validator: JSON import must target a live project and valid nested geometry."""
from fastapi import HTTPException

from app.infrastructure.validation import validate


def require_project(repo, pid):
    return repo.get(pid)


def _pieces_ok(payload):
    pieces = payload.get("pieces") if isinstance(payload, dict) else None
    return bool(pieces) and all(piece.get("points") for piece in pieces)


def assert_importable(body):
    pattern = body.pattern
    if pattern.get("schema_version") != 1:
        raise HTTPException(422, "Unsupported geometry schema version")
    if not _pieces_ok(pattern):
        raise HTTPException(422, "Imported pattern must contain non-empty piece geometry")
    for grade in body.grades:
        if not _pieces_ok(grade):
            raise HTTPException(422, "Imported grades must contain non-empty piece geometry")
        try:
            grade_issues = validate(grade)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, "Imported grades have an invalid pattern structure") from exc
        if any(issue["severity"] == "ERROR" for issue in grade_issues):
            raise HTTPException(422, "Imported grades failed deterministic validation")
    if body.marker is not None:
        placements = body.marker.get("placements") if isinstance(body.marker, dict) else None
        if not isinstance(placements, list):
            raise HTTPException(422, "Imported marker placements must be a list")
    try:
        issues = validate(pattern)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, "Imported geometry has an invalid pattern structure") from exc
    if any(issue["severity"] == "ERROR" for issue in issues):
        raise HTTPException(422, "Imported geometry failed deterministic validation")
    return issues
