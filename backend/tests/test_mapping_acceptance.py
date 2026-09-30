"""Structured mapping acceptance must confirm and must not mutate values."""
from fastapi.testclient import TestClient

from app.api.main import create_app


def test_accept_mapping_requires_confirmation_and_leaves_values_unchanged(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/map.db"))
    pid = client.post("/api/v1/projects", json={"name": "Map", "demo": True}).json()["id"]
    before = client.get(f"/api/v1/projects/{pid}").json()
    action = client.post(
        f"/api/v1/projects/{pid}/assistant/propose",
        json={"prompt": 'Accept mapping of "shoulder breadth" as shoulder_point_to_point', "size": "L"},
    ).json()
    assert action["intent"] == "accept_mapping"
    assert action["requires_confirmation"] is True
    assert action["parameters"] == {
        "source_label": "shoulder breadth",
        "canonical_key": "shoulder_point_to_point",
    }
    denied = client.post(
        f"/api/v1/projects/{pid}/assistant/execute",
        json={"proposal_id": action["id"], "confirmed": False},
    )
    assert denied.status_code == 409
    done = client.post(
        f"/api/v1/projects/{pid}/assistant/execute",
        json={"proposal_id": action["id"], "confirmed": True},
    )
    assert done.status_code == 200
    project = done.json()["project"]
    assert project["measurements"] == before["measurements"]
    assert project["accepted_mappings"]["shoulder breadth"] == "shoulder_point_to_point"
    assert done.json()["validation"]["status"] == "NO_VALUE_CHANGE"
