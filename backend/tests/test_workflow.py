from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.parsers import parse_xlsx

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        yield c


def test_workbook_formula_and_decimal():
    rows = parse_xlsx((ROOT / "references/Book2(4).xlsx").read_bytes(), "Book2(4).xlsx")
    chest = next(r for r in rows if r["key"] == "half_chest")
    assert chest["values"]["L"]["value"] == 58
    assert chest["values"]["S"]["value"] == 54
    assert chest["values"]["M"]["formula"] == "=G7-2"
    assert next(r for r in rows if r["key"] == "collar_width_cb")["values"]["L"]["value"] == 4.7


def test_demo_end_to_end(client):
    p = client.post("/api/v1/projects", json={"name": "Demo", "demo": True}).json()
    base = f"/api/v1/projects/{p['id']}"
    assert client.post(base + "/patterns/generate", json={"size": "L"}).status_code == 409
    for key, value in [
        ("units", "cm"),
        ("profile", "demo_v1"),
        ("review", "confirmed"),
        ("placket", "workbook"),
    ]:
        assert client.post(base + f"/requirements/{key}/resolve", json={"value": value}).status_code == 200
    result = client.post(base + "/patterns/generate", json={"size": "L"})
    assert result.status_code == 200, result.text
    pattern = result.json()
    assert len(pattern["pieces"]) == 8
    assert not any(v["severity"] == "ERROR" for v in pattern["validation"])
    grades = client.post(base + "/grade", json={"sizes": ["S", "M", "L", "XL", "XXL", "3XL"]})
    assert grades.status_code == 200, grades.text
    assert len(grades.json()) == 6
    marker = client.post(
        base + "/markers/generate", json={"width": 150, "quantity": 2, "gap": 0.5, "size": "L"}
    )
    assert marker.status_code == 200, marker.text
    assert 0 < marker.json()["utilization"] <= 100
    for kind in ["svg", "json", "pdf", "marker-svg", "marker-pdf"]:
        export = client.get(base + f"/exports/{kind}")
        assert export.status_code == 200 and len(export.content) > 100
    assert client.get(base).json()["pattern"]["id"] == pattern["id"]


def test_upload_and_invalid_requests(client):
    p = client.post("/api/v1/projects", json={"name": "Import"}).json()
    base = f"/api/v1/projects/{p['id']}"
    assert (
        client.post(
            base + "/documents", files={"file": ("bad.exe", b"no", "application/octet-stream")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            base + "/documents",
            files={
                "file": (
                    "bad.xlsx",
                    b"no",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        ).status_code
        == 415
    )
    with (ROOT / "references/Book2(4).xlsx").open("rb") as f:
        assert (
            client.post(
                base + "/documents",
                files={
                    "file": (
                        "book.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            ).status_code
            == 200
        )
    assert len(client.get(base).json()["measurements"]) == 35
    assert client.post(base + "/patterns/generate", json={"size": "4XL"}).status_code == 422
    assert client.get("/api/v1/projects/absent").status_code == 404
