"""P0-06: scalar fields that persistence projects into SQL columns are type-checked on import (422, not 500/404)."""
from types import SimpleNamespace

import pytest

from app.application.errors import ImportInvalid
from app.infrastructure.import_fields import check_fields


def _first_piece(body):
    return body["pattern"]["pieces"][0]


def _nested(depth):
    value: list = []
    for _ in range(depth):
        value = [value]
    return value


@pytest.mark.parametrize(("mutate", "code"), [
    (lambda b: b["pattern"].update(id=5), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].update(profile=["demo_v1"]), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["grades"][0].pop("input_hash"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].update(created_at=["today"]), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: _first_piece(b).pop("quantity"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: _first_piece(b).pop("id"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"]["validation"].append({"severity": "WARNING", "code": ["x"], "message": "m"}),
     "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["grades"][0].update(id=b["pattern"]["id"]), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].update(extra=_nested(500)), "IMPORT_VALUE_INVALID"),
    (lambda b: b["marker"].update(strategy=["first_fit"]), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"].pop("waste"), "IMPORT_MARKER_INVALID"),
], ids=["int-id", "list-profile", "missing-input-hash", "list-created-at", "missing-quantity",
        "missing-piece-id", "list-issue-code", "grade-reuses-pattern-id", "deep-nesting", "list-marker-strategy", "missing-marker-waste"])
def test_projection_fields_are_type_checked(exported, import_mutated, mutate, code):
    client, url, _ = exported
    before = client.get(url).json()["pattern"]["id"]
    response = import_mutated(mutate)
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert client.get(url).json()["pattern"]["id"] == before


def test_field_check_rejects_missing_pieces_on_its_own():
    version = {"id": "v1", "profile": "demo_v1", "input_hash": "h", "validation": []}
    with pytest.raises(ImportInvalid) as caught:
        check_fields(SimpleNamespace(pattern=version, grades=[], marker=None))
    assert caught.value.code == "IMPORT_GEOMETRY_INVALID"
