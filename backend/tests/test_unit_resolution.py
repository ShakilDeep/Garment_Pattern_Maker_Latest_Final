import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def demo(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/units.db")) as client:
        pid = client.post("/api/v1/projects", json={"name": "Units", "demo": True}).json()["id"]
        yield client, f"/api/v1/projects/{pid}"


def _resolve(client, url, key, value):
    return client.post(f"{url}/requirements/{key}/resolve", json={"value": value})


def _row(client, url, key):
    return next(r for r in client.get(url).json()["measurements"] if r["key"] == key)


def test_inch_workbook_is_converted_exactly_to_cm(demo):
    client, url = demo
    assert _resolve(client, url, "units", "inch").status_code == 200
    chest = _row(client, url, "half_chest")
    assert chest["values"]["L"]["value"] == 147.32  # 58 in * 2.54
    assert chest["values"]["L"]["unit_source_value"] == 58
    assert chest["unit"] == "cm" and chest["source_unit"] == "inch"
    tolerance = next(r for r in client.get(url).json()["measurements"] if r["tolerance"] == 1.778)
    assert tolerance["tolerance_source"] == 0.7


def test_switching_units_back_restores_the_original_values(demo):
    client, url = demo
    before = client.get(url).json()["measurements"]
    for unit in ("cm", "inch", "cm"):
        assert _resolve(client, url, "units", unit).status_code == 200
    after = client.get(url).json()["measurements"]
    for old, new in zip(before, after, strict=True):
        assert {s: c["value"] for s, c in old["values"].items()} == {s: c["value"] for s, c in new["values"].items()}
        assert old["tolerance"] == new["tolerance"]


def test_manual_override_is_already_cm_and_is_not_converted(demo):
    client, url = demo
    _resolve(client, url, "units", "cm")
    edit = client.patch(f"{url}/measurements/half_chest", json={"size": "L", "changes": {"half_chest": 59.5}})
    assert edit.status_code == 200, edit.text
    assert _resolve(client, url, "units", "inch").status_code == 200
    assert _row(client, url, "half_chest")["values"]["L"]["value"] == 59.5


def test_unsupported_unit_is_refused(demo):
    client, url = demo
    response = _resolve(client, url, "units", "mm")
    assert response.status_code == 400
    assert "Unsupported requirement resolution" in response.json()["message"]


def test_requirement_offers_cm_and_inch(demo):
    client, url = demo
    units = next(i for i in client.get(f"{url}/requirements").json()["items"] if i["key"] == "units")
    assert units["options"] == ["cm", "inch"]
    assert units["accepted_units"] == ["cm", "inch"]


def test_inch_edit_is_stored_on_the_model_grid(demo):
    client, url = demo
    _resolve(client, url, "units", "cm")
    noisy = 18.1 * 2.54  # 45.974000000000004 from the browser's inch conversion
    response = client.patch(f"{url}/measurements/half_chest", json={"size": "L", "changes": {"half_chest": noisy}})
    assert response.status_code == 200, response.text
    assert _row(client, url, "half_chest")["values"]["L"]["value"] == 45.974
