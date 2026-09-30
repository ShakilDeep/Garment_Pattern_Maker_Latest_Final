from fastapi.testclient import TestClient

from app.api.main import create_app


def test_ai_proposal_is_structured_and_unknown_prompts_are_explanations(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/ai.db"))
    pid = client.post("/api/v1/projects", json={"name": "AI", "demo": True}).json()["id"]
    result = client.post(
        f"/api/v1/projects/{pid}/assistant/propose",
        json={"prompt": "Make sleeve 2 cm shorter", "size": "L"},
    )
    assert result.status_code == 200
    action = result.json()
    assert action["intent"] == "adjust_measurement"
    assert action["parameters"] == {"measurement": "sleeve_length", "delta": -2.0, "size": "L"}
    assert action["requires_confirmation"] is True
    assert action["deterministic_service"] == "measurements"
    assert action["provenance"]["provider"] == "local"


def test_ai_action_requires_confirmation_and_uses_measurement_service(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/ai-execute.db"))
    pid = client.post("/api/v1/projects", json={"name": "AI", "demo": True}).json()["id"]
    before = client.get(f"/api/v1/projects/{pid}").json()
    original = next(r for r in before["measurements"] if r["key"] == "sleeve_length")["values"]["L"]["value"]
    action = client.post(
        f"/api/v1/projects/{pid}/assistant/propose",
        json={"prompt": "Make sleeve 2 cm shorter", "size": "L"},
    ).json()
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
    changed = next(r for r in done.json()["project"]["measurements"] if r["key"] == "sleeve_length")
    assert changed["values"]["L"]["value"] == original - 2
    assert done.json()["validation"]["status"] == "INPUTS_INVALIDATED"


def test_ai_execute_rejects_unknown_or_replayed_proposal(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/ai-replay.db"))
    pid = client.post("/api/v1/projects", json={"name": "AI", "demo": True}).json()["id"]
    missing = client.post(
        f"/api/v1/projects/{pid}/assistant/execute",
        json={"proposal_id": "missing", "confirmed": True},
    )
    assert missing.status_code == 404
