"""Explicit catalog mapping, guided requirement queue, marker comparison."""
from io import BytesIO

import openpyxl
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.domain.catalog import MAPPING
from app.infrastructure.parsers import parse_xlsx


def _workbook(code, label="Chest"):
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["Codes", "MEASUREMENTS POINTS", "S", "M"])
    sheet.append([code, label, 50, 52])
    data = BytesIO()
    wb.save(data)
    return data.getvalue()


def test_xlsx_mapping_is_explicit_and_never_guesses_unknown_codes():
    mapped = parse_xlsx(_workbook("11264", "Sleeve"), "map.xlsx")[0]
    unknown = parse_xlsx(_workbook("ZZZ-99", "Mystery"), "unk.xlsx")[0]
    assert mapped["key"] == MAPPING["11264"]
    assert mapped["mapping_status"] == "catalog"
    assert mapped["mapped_from"] == "11264"
    assert unknown["key"] == "ZZZ-99"
    assert unknown["mapping_status"] == "unmapped"
    assert unknown["mapped_from"] is None
    assert unknown["key"] not in MAPPING.values()


def test_requirements_queue_orders_blockers_and_names_next(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/queue.db"))
    pid = client.post("/api/v1/projects", json={"name": "Queue", "demo": True}).json()["id"]
    result = client.get(f"/api/v1/projects/{pid}/requirements/queue", params={"size": "L"})
    assert result.status_code == 200
    body = result.json()
    assert body["remaining"] == len(body["items"]) > 0
    assert body["next"]["key"] == body["items"][0]["key"]
    statuses = [item["status"] for item in body["items"]]
    rank = {"MISSING": 0, "CONFLICTING": 1, "AMBIGUOUS": 2, "DEMO_DEFAULT_AVAILABLE": 3}
    assert statuses == sorted(statuses, key=lambda status: rank.get(status, 9))


def test_marker_compare_reports_utilization_and_length_delta(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/cmp.db"))
    pid = client.post("/api/v1/projects", json={"name": "Compare", "demo": True}).json()["id"]
    base = f"/api/v1/projects/{pid}"
    for key, value in {"units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook"}.items():
        assert client.post(f"{base}/requirements/{key}/resolve", json={"value": value}).status_code == 200
    assert client.post(f"{base}/patterns/generate", json={"size": "L", "allowance": 0}).status_code == 200
    empty = client.get(f"{base}/markers/compare")
    assert empty.status_code == 409
    first = client.post(f"{base}/markers/generate", json={"width": 150, "size": "L"}).json()
    client.post(f"{base}/markers/generate", json={"width": 200, "size": "L"})
    compared = client.get(f"{base}/markers/compare")
    assert compared.status_code == 200
    body = compared.json()
    assert body["current_width"] == 200
    assert body["previous_width"] == 150
    assert body["length_delta"] == body["current_length"] - first["length"]
