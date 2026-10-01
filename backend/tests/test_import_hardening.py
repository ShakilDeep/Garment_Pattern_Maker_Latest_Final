"""P0-06 / defect c: geometry import validates values, schema, sizes and markers with specific 422 codes."""
from pathlib import Path

import pytest
from test_integrity import _ready

APP = Path(__file__).resolve().parents[1] / "app"


def test_export_with_marker_round_trips(exported, import_mutated):
    response = import_mutated(lambda body: None)
    assert response.status_code == 200
    assert response.json()["marker"]["pattern_ids"] == exported[2]["marker"]["pattern_ids"]


@pytest.mark.parametrize(("sizes", "quantities"), [(["L", "M"], {"L": 1}), (["S"], {"L": 2})])
def test_single_size_markers_and_base_size_grades_round_trip(tmp_path, sizes, quantities):
    client, url = _ready(tmp_path)
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    assert client.post(f"{url}/grade", json={"sizes": sizes}).status_code == 200
    assert client.post(f"{url}/markers/generate", json={"width": 150, "quantities": quantities}).status_code == 200
    payload = client.get(f"{url}/exports/json").json()
    assert client.post(f"{url}/exports/import", json=payload).status_code == 200


@pytest.mark.parametrize(("mutate", "code"), [
    (lambda b: b["marker"]["placements"][0].update(x=10**400), "IMPORT_VALUE_INVALID"),
    (lambda b: b["pattern"]["pieces"][0]["points"][0].__setitem__(0, 10**400), "IMPORT_VALUE_INVALID"),
    (lambda b: b["marker"].update(utilization=float("nan")), "IMPORT_VALUE_INVALID"),
    (lambda b: b["pattern"].update(size="4XL"), "IMPORT_SIZES_INVALID"),
    (lambda b: b["pattern"].update(size=["L"]), "IMPORT_SIZES_INVALID"),
    (lambda b: b["pattern"]["pieces"][0].update(cut_points="abc"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"]["pieces"][0].update(quantity="x"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].update(validation="x"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].pop("validation"), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["pattern"].update(schema_version=2), "IMPORT_SCHEMA_UNSUPPORTED"),
    (lambda b: b["grades"][0].update(schema_version=2), "IMPORT_SCHEMA_UNSUPPORTED"),
    (lambda b: b["grades"][1].update(size=b["grades"][0]["size"]), "IMPORT_SIZES_INVALID"),
    (lambda b: b["grades"][0].update(size="4XL"), "IMPORT_SIZES_INVALID"),
    (lambda b: b["grades"][0].update(pieces=[]), "IMPORT_GEOMETRY_INVALID"),
    (lambda b: b["marker"]["pattern_ids"].update(S="not-imported"), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"].update(pattern_ids={}), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"]["placements"][0].update(x=b["marker"]["width"] + 10), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"]["placements"][0].update(points=[[0, 0], [1, 0]]), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"]["placements"][0].update(y="top"), "IMPORT_MARKER_INVALID"),
    (lambda b: b["marker"].update(placements="invalid"), "IMPORT_MARKER_INVALID"),
], ids=["huge-placement-x", "huge-point", "nan-utilization", "pattern-size-4xl", "pattern-size-list",
        "cut-points-string", "quantity-string", "validation-string", "validation-missing", "pattern-schema", "grade-schema", "duplicate-size", "unknown-size", "empty-grade",
        "foreign-pattern-id", "no-pattern-ids", "placement-off-fabric", "degenerate-points",
        "non-numeric-y", "placements-not-list"])
def test_invalid_import_is_rejected_with_specific_code(exported, import_mutated, mutate, code):
    client, url, _ = exported
    before = client.get(url).json()["pattern"]["id"]
    response = import_mutated(mutate)
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert client.get(url).json()["pattern"]["id"] == before


def test_grade_request_rejects_duplicate_sizes(exported):
    client, url, _ = exported
    response = client.post(f"{url}/grade", json={"sizes": ["L", "L"]})
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_INVALID"


def test_inner_layers_do_not_import_fastapi():
    offenders = [str(path.relative_to(APP)) for layer in ("domain", "application", "infrastructure")
                 for path in (APP / layer).rglob("*.py") if "fastapi" in path.read_text(encoding="utf-8")]
    assert offenders == []
