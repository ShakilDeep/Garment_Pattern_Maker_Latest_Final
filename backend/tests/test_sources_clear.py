"""Clearing sources lets the same workbook be imported again after Reset."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "references" / "Book2(4).xlsx"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/sources.db")) as c:
        yield c


def test_duplicate_import_rejected_until_sources_cleared(client):
    p = client.post("/api/v1/projects", json={"name": "Reimport"}).json()
    base = f"/api/v1/projects/{p['id']}"
    data = XLSX.read_bytes()
    first = client.post(f"{base}/documents", files={
        "file": ("Book2(4).xlsx", data,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    })
    assert first.status_code == 200
    dup = client.post(f"{base}/documents", files={
        "file": ("Book2(4).xlsx", data,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    })
    assert dup.status_code == 409
    assert "already been imported" in dup.json()["message"]

    cleared_response = client.post(f"{base}/sources/clear")
    assert cleared_response.status_code == 200
    cleared = client.get(base).json()
    assert cleared["documents"] == []
    assert cleared["measurements"] == []
    assert cleared["pattern"] is None

    again = client.post(f"{base}/documents", files={
        "file": ("Book2(4).xlsx", data,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    })
    assert again.status_code == 200
    restored = client.get(base).json()
    assert len(restored["documents"]) == 1
    assert restored["measurements"]
