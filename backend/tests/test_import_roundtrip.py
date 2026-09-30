"""JSON geometry export must round-trip onto a persisted project."""
from fastapi.testclient import TestClient

from app.api.main import create_app


def _ready(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/roundtrip.db"))
    pid = client.post("/api/v1/projects", json={"name": "Roundtrip", "demo": True}).json()["id"]
    url = f"/api/v1/projects/{pid}"
    for key, value in {
        "units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook",
    }.items():
        assert client.post(f"{url}/requirements/{key}/resolve", json={"value": value}).status_code == 200
    return client, url


def test_json_export_import_persists_pattern_on_target_project(tmp_path):
    client, url = _ready(tmp_path)
    generated = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    assert client.post(f"{url}/grade", json={"sizes": ["M"]}).status_code == 200
    payload = client.get(f"{url}/exports/json").json()
    target = client.post("/api/v1/projects", json={"name": "Restore"}).json()
    response = client.post(f"/api/v1/projects/{target['id']}/exports/import", json=payload)
    restored = client.get(f"/api/v1/projects/{target['id']}").json()
    assert response.status_code == 200
    assert restored["pattern"]["id"] == generated["id"]
    assert restored["pattern"]["pieces"] == payload["pattern"]["pieces"]
    assert restored["grades"][0]["size"] == "M"
    assert restored["pattern"].get("stale") is False
