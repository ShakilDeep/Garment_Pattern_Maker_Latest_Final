"""Clearing the current pattern empties studio preview until regenerate."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/clear.db")) as c:
        yield c


def test_clear_pattern_removes_preview_geometry(client):
    p = client.post("/api/v1/projects", json={"name": "Clear", "demo": True}).json()
    base = f"/api/v1/projects/{p['id']}"
    for key, value in [
        ("units", "cm"),
        ("profile", "demo_v1"),
        ("review", "confirmed"),
        ("placket", "workbook"),
    ]:
        assert client.post(f"{base}/requirements/{key}/resolve", json={"value": value}).status_code == 200
    assert client.post(base + "/patterns/generate", json={"size": "M", "allowance": 1}).status_code == 200
    before = client.get(base).json()
    assert before["pattern"] is not None
    assert client.post(base + "/patterns/clear").status_code == 200
    after = client.get(base).json()
    assert after["pattern"] is None
    assert after["grades"] == []
    assert after["marker"] is None
