from collections import Counter

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, box

from app.api.main import create_app


@pytest.fixture
def ready(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/batch.db")) as client:
        p = client.post("/api/v1/projects", json={"name": "Batch test", "demo": True}).json()
        base = f"/api/v1/projects/{p['id']}"
        for key, value in {"units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook"}.items():
            assert client.post(base + f"/requirements/{key}/resolve", json={"value": value}).status_code == 200
        assert client.post(base + "/patterns/generate", json={"size": "L", "allowance": 1}).status_code == 200
        assert client.post(base + "/grade", json={"sizes": ["S", "L"]}).status_code == 200
        yield client, base


def test_mixed_size_quantities_geometry_and_provenance(ready):
    client, base = ready
    body = {"width": 150, "gap": 0.5, "quantities": {"S": 2, "L": 1}}
    response = client.post(base + "/markers/generate", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["quantities"] == {"S": 2, "L": 1}
    assert result["quantity"] == 3
    assert Counter(p["size"] for p in result["placements"]) == {"S": 32, "L": 16}
    grades = client.get(base).json()["grades"]
    assert result["pattern_ids"] == {g["size"]: g["id"] for g in grades}
    shapes = []
    for p in result["placements"]:
        assert p["pattern_id"] == result["pattern_ids"][p["size"]]
        assert p["rotation"] == 0
        shape = Polygon([(x + p["x"], y + p["y"]) for x, y in p["points"]])
        assert box(0, 0, result["width"], result["length"]).covers(shape)
        assert all(shape.distance(other) >= 0.5 - 1e-6 for other in shapes)
        shapes.append(shape)
    assert result["utilization"] == pytest.approx(100 * sum(s.area for s in shapes) / (150 * result["length"]))
    body["quantities"] = {"L": 1, "S": 2}
    assert client.post(base + "/markers/generate", json=body).json() == result


@pytest.mark.parametrize("quantities", [{}, {"S": 0}, {"L": -1}, {"S": 1.5}, {"S": True}, {"S": "2"}, {"4XL": 1}, {"S": 11, "L": 10}])
def test_invalid_batch_quantities(ready, quantities):
    client, base = ready
    response = client.post(base + "/markers/generate", json={"width": 150, "quantities": quantities})
    assert response.status_code == 422, response.text
    assert client.get(base).json()["marker"] is None


def test_unavailable_size_preserves_previous_result(ready):
    client, base = ready
    old = client.post(base + "/markers/generate", json={"width": 150, "size": "L"}).json()
    response = client.post(base + "/markers/generate", json={"width": 150, "quantities": {"S": 1, "M": 1}})
    assert response.status_code == 409, response.text
    assert "M" in response.text
    assert client.get(base).json()["marker"] == old


@pytest.mark.parametrize("action,body", [
    ("/grade", {"sizes": ["S", "L"]}),
    ("/patterns/generate", {"size": "L", "allowance": 2}),
    ("/requirements/review/resolve", {"value": "confirmed"}),
])
def test_changed_pattern_versions_invalidate_both_markers(ready, action, body):
    client, base = ready
    for width in [150, 160]:
        assert client.post(base + "/markers/generate", json={"width": width, "size": "L"}).status_code == 200
    assert client.get(base).json()["previous_marker"] is not None
    assert client.post(base + action, json=body).status_code == 200
    p = client.get(base).json()
    assert p["marker"] is None
    assert p["previous_marker"] is None
