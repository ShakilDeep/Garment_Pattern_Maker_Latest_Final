"""Pagination for project list and outline-quality validation codes."""
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.validation import validate


def test_projects_list_honors_limit_offset_and_total_header(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/pages.db"))
    client.post("/api/v1/projects", json={"name": "Alpha"})
    client.post("/api/v1/projects", json={"name": "Beta"})
    page = client.get("/api/v1/projects", params={"limit": 1, "offset": 0})
    rest = client.get("/api/v1/projects")
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.headers["x-total-count"] == "2"
    assert len(rest.json()) == 2


def test_outline_quality_flags_spike_and_flattening():
    spike = {
        "name": "Spike",
        "points": [[0, 0], [10, 0], [0.05, 0.01], [0, 6], [0, 0]],
        "notches": [],
        "grainline": [[1, 2], [1, 4]],
    }
    flat = {
        "name": "Flat",
        "points": [[0, 0], [4, 0], [8, 0], [8, 6], [0, 6], [0, 0]],
        "notches": [],
        "grainline": [[2, 2], [2, 4]],
    }
    issues = validate({"pieces": [spike, flat], "seam_allowance": 0, "measurements": {}})
    assert any(i["code"] == "TURN_ANGLE" and i["piece"] == "Spike" for i in issues)
    assert any(i["code"] == "FLATTENING" and i["piece"] == "Flat" for i in issues)
