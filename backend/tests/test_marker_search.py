import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def ready(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/search.db")) as client:
        p = client.post("/api/v1/projects", json={"name": "Search test", "demo": True}).json()
        base = f"/api/v1/projects/{p['id']}"
        for key, value in {"units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook"}.items():
            assert client.post(base + f"/requirements/{key}/resolve", json={"value": value}).status_code == 200
        assert client.post(base + "/patterns/generate", json={"size": "L", "allowance": 1}).status_code == 200
        yield client, base


def test_marker_search_reports_iterations_within_budget(ready):
    client, base = ready
    body = {
        "width": 150, "gap": 0.5, "size": "L",
        "seed": 7, "iterations": 4, "time_budget_ms": 500,
    }
    response = client.post(base + "/markers/generate", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["seed"] == 7
    assert result["iterations"] == 4
    assert 1 <= result["iterations_run"] <= 4
    assert result["time_budget_ms"] == 500
    again = client.post(base + "/markers/generate", json=body).json()
    assert again["placements"] == result["placements"]
