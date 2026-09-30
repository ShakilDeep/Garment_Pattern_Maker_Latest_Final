"""Regression for scoped writes, archived sources, import, and versioned grading."""
from fastapi.testclient import TestClient

from app.api.main import create_app


def _ready(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/integrity.db"))
    pid = client.post("/api/v1/projects", json={"name": "Integrity", "demo": True}).json()["id"]
    url = f"/api/v1/projects/{pid}"
    for key, value in {
        "units": "cm",
        "profile": "demo_v1",
        "review": "confirmed",
        "placket": "workbook",
    }.items():
        assert client.post(f"{url}/requirements/{key}/resolve", json={"value": value}).status_code == 200
    return client, url


def test_measurement_route_rejects_unrelated_changes(tmp_path):
    client, url = _ready(tmp_path)
    response = client.patch(
        f"{url}/measurements/half_chest",
        json={"size": "L", "changes": {"sleeve_length": -3}},
    )
    row = next(r for r in client.get(url).json()["measurements"] if r["key"] == "sleeve_length")
    assert response.status_code in (400, 422)
    assert row["values"]["L"]["value"] > 0


def test_archived_source_blocks_generation(tmp_path):
    client, url = _ready(tmp_path)
    document = next(d for d in client.get(url).json()["documents"] if d["filename"].endswith(".xlsx"))
    assert client.post(f"{url}/documents/{document['id']}/archive").status_code == 200
    check = client.get(f"{url}/requirements").json()
    response = client.post(f"{url}/patterns/generate", json={"size": "L"})
    assert check["ready"] is False
    assert response.status_code == 409


def test_import_rejects_invalid_nested_geometry(tmp_path):
    client, url = _ready(tmp_path)
    pattern = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    response = client.post(
        f"{url}/exports/import",
        json={
            "schema_version": 1,
            "project": "Integrity",
            "pattern": pattern,
            "grades": [{"size": "M", "pieces": []}],
            "marker": {"placements": "invalid"},
        },
    )
    assert response.status_code == 422


def test_import_checks_project_exists(tmp_path):
    client, url = _ready(tmp_path)
    pattern = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    response = client.post(
        "/api/v1/projects/nonexistent/exports/import",
        json={"schema_version": 1, "project": "Integrity", "pattern": pattern},
    )
    assert response.status_code == 404


def test_version_scoped_grade_uses_requested_version(tmp_path):
    client, url = _ready(tmp_path)
    old = client.post(f"{url}/patterns/generate", json={"size": "L", "allowance": 0}).json()
    assert client.post(f"{url}/patterns/generate", json={"size": "L", "allowance": 2}).status_code == 200
    response = client.post(f"{url}/patterns/{old['id']}/grade", json={"sizes": ["M"]})
    assert response.status_code == 200
    assert [p["seam_allowance"] for p in response.json()] == [0]
