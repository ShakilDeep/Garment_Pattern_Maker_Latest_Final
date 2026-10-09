"""T126c: chart view, AI mapping suggestions and the user's confirmation over HTTP."""
import pytest
from fastapi.testclient import TestClient
from pom_workbooks import CL1086464, workbook_bytes
from test_pom_mapping_confirm import Fake

from app.api.main import create_app

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
UNKNOWN = workbook_bytes(("Chart", [
    ["Codes", "MEASUREMENTS POINTS", "S", "M"],
    ["A1", "1/2 WAIST", 35, 37],
    ["Z9", "1/2 HIPS", 48, 50],
]))


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path}/map.db", pom_suggester=Fake())
    with TestClient(app) as test_client:
        yield test_client


def _project(client, workbook=UNKNOWN):
    pid = client.post("/api/v1/projects", json={"name": "Map"}).json()["id"]
    base = f"/api/v1/projects/{pid}"
    assert client.post(base + "/documents", files={"file": ("c.xlsx", workbook, XLSX)}).status_code == 200
    return base


def _keys(client, base):
    items = client.get(base + "/requirements", params={"size": "S"}).json()["items"]
    return {item["key"] for item in items}


def test_the_chart_view_lists_rows_with_their_status_and_base_value(client):
    chart = client.get(_project(client) + "/chart").json()
    assert chart["sizes"] == ["S", "M"] and "half_seat" in chart["canonical_keys"]
    rows = {row["row"]: row for row in chart["rows"]}
    assert (rows[3]["label"], rows[3]["status"], rows[3]["base_value"]) == ("1/2 HIPS", "unmapped", 48)
    assert (rows[2]["key"], rows[2]["status"], rows[2]["half"]) == ("half_waist", "synonym", True)


def test_suggest_then_confirm_clears_the_missing_information_item(client):
    base = _project(client)
    assert "mapping:3" in _keys(client, base)
    suggested = client.post(base + "/mappings/suggest").json()
    assert suggested == [{"row": 3, "key": "half_seat", "confidence": 0.9, "provider": "gemini",
                          "reason": "hips = seat"}]
    assert client.get(base + "/chart").json()["rows"][1]["suggestion"]["key"] == "half_seat"
    assert "mapping:3" in _keys(client, base)  # a suggestion alone changes nothing
    project = client.post(base + "/mappings/3", json={"key": "half_seat"}).json()
    row = next(r for r in project["measurements"] if r["row"] == 3)
    assert (row["key"], row["mapped_from"]) == ("half_seat", "ai:gemini")
    assert project["audit"][-1]["event"] == "mapping_confirmed"
    assert "mapping:3" not in _keys(client, base)
    assert client.post(base + "/history/undo").json()["measurements"][1]["mapping_status"] == "unmapped"


def test_marking_not_used_clears_the_item(client):
    base = _project(client)
    assert client.post(base + "/mappings/3", json={"not_used": True}).status_code == 200
    assert "mapping:3" not in _keys(client, base)


@pytest.mark.parametrize(("row", "body", "status", "code"), [
    (3, {"key": "half_waist"}, 400, "INPUT_INVALID"),
    (3, {"key": "half_seat", "not_used": True}, 422, "REQUEST_INVALID"),
    (3, {}, 422, "REQUEST_INVALID"),
    (77, {"key": "half_seat"}, 404, "NOT_FOUND"),
])
def test_invalid_confirmations_are_rejected(client, row, body, status, code):
    response = client.post(_project(client) + f"/mappings/{row}", json=body)
    assert (response.status_code, response.json()["code"]) == (status, code)


def test_a_fully_mapped_chart_has_nothing_to_suggest(client):
    assert client.post(_project(client, CL1086464.read_bytes()) + "/mappings/suggest").json() == []


def test_a_project_without_a_chart_has_no_chart_view(client):
    pid = client.post("/api/v1/projects", json={"name": "Empty"}).json()["id"]
    assert client.get(f"/api/v1/projects/{pid}/chart").status_code == 409
