from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.ai_provider import LocalAIProvider


class StubProvider:
    name = "stub"
    model = "test"

    def __init__(self, output):
        self.output = output

    def propose(self, prompt, size, *, context=None):
        if isinstance(self.output, Exception):
            raise self.output
        return deepcopy(self.output)


def proposal(**changes):
    raw = LocalAIProvider().propose("Make sleeve 2 cm shorter", "L")
    return {**raw, **changes}


def setup_client(tmp_path, output):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/trust.db", ai_provider=StubProvider(output)))
    project = client.post("/api/v1/projects", json={"name": "AI", "demo": True}).json()
    return client, f"/api/v1/projects/{project['id']}", project


@pytest.mark.parametrize(
    "output",
    [
        None,
        [],
        "secret raw provider output",
        {},
        proposal(intent="write_coordinates"),
        proposal(parameters={"measurement": "sleeve_length", "delta": -2, "size": "L", "points": []}),
        proposal(parameters={"measurement": "unknown", "delta": -2, "size": "L"}),
        proposal(parameters={"measurement": "sleeve_length", "delta": "-2", "size": "L"}),
        proposal(parameters={"measurement": "sleeve_length", "delta": float("nan"), "size": "L"}),
        proposal(parameters={"measurement": "sleeve_length", "delta": -2, "size": "XS"}),
        proposal(parameters={}),
        proposal(requires_confirmation=False),
        proposal(deterministic_service="none"),
        proposal(target="project"),
        proposal(confidence=2),
        proposal(status="EXECUTED"),
    ],
)
def test_invalid_provider_output_is_rejected_without_persistence(tmp_path, output):
    client, url, before = setup_client(tmp_path, output)
    response = client.post(f"{url}/assistant/propose", json={"prompt": "edit"})
    assert response.status_code == 502
    assert response.json()["code"] == "AI_OUTPUT_INVALID"
    assert "secret" not in response.text
    assert response.json()["correlation_id"] == response.headers["x-request-id"]
    assert client.get(url).json() == before


def test_provider_unavailable_preserves_manual_workflow(tmp_path, caplog):
    client, url, before = setup_client(tmp_path, RuntimeError("secret credential"))
    response = client.post(f"{url}/assistant/propose", json={"prompt": "edit"})
    assert response.status_code == 503
    assert response.json()["code"] == "AI_UNAVAILABLE"
    assert "secret" not in response.text
    assert "secret" not in caplog.text
    assert client.get(url).json() == before
    assert (
        client.patch(f"{url}/measurements", json={"size": "L", "changes": {"sleeve_length": 60}}).status_code
        == 200
    )


def test_injected_action_requires_confirmation_and_cannot_be_replayed(tmp_path):
    client, url, _ = setup_client(tmp_path, proposal())
    action = client.post(f"{url}/assistant/propose", json={"prompt": "edit"}).json()
    assert action["provenance"]["provider"] == "stub"
    body = {"proposal_id": action["id"], "confirmed": False}
    assert client.post(f"{url}/assistant/execute", json=body).status_code == 409
    body["confirmed"] = True
    assert client.post(f"{url}/assistant/execute", json=body).status_code == 200
    after = client.get(url).json()
    assert client.post(f"{url}/assistant/execute", json=body).status_code == 409
    assert client.get(url).json() == after


@pytest.mark.parametrize(
    "prompt,parameters",
    [
        ("set 1 cm seam allowance", {"value": 4}),
        ("generate size L", {"size": "XS"}),
        ("optimize marker 150 cm", {"size": "L", "width": 150, "quantity": True, "gap": 0.5}),
        ("optimize marker 150 cm", {"size": "L", "width": 150, "quantity": 21, "gap": 0.5}),
        ("optimize marker 150 cm", {"size": "L", "width": 20, "quantity": 1, "gap": 0.5}),
        ("optimize marker 150 cm", {"size": "L", "width": 150, "quantity": 1, "gap": 0}),
        ("explain validation", {"answer": ""}),
    ],
)
def test_each_action_validates_its_parameters(tmp_path, prompt, parameters):
    raw = LocalAIProvider().propose(prompt, "L")
    client, url, before = setup_client(tmp_path, {**raw, "parameters": parameters})
    assert client.post(f"{url}/assistant/propose", json={"prompt": prompt}).status_code == 502
    assert client.get(url).json() == before


def test_action_rechecks_current_measurement_before_execution(tmp_path):
    client, url, _ = setup_client(tmp_path, proposal())
    action = client.post(f"{url}/assistant/propose", json={"prompt": "edit"}).json()
    client.patch(f"{url}/measurements", json={"size": "L", "changes": {"sleeve_length": 1}})
    before = client.get(url).json()
    response = client.post(f"{url}/assistant/execute", json={"proposal_id": action["id"], "confirmed": True})
    assert response.status_code == 400
    assert client.get(url).json() == before


@pytest.mark.parametrize("size", ["S", "M", "L", "XL", "XXL", "3XL"])
def test_local_generation_recognizes_whole_size_tokens(size):
    action = LocalAIProvider().propose(f"generate size {size}", "L")
    assert action["parameters"] == {"size": size}


def test_local_marker_generation_is_not_pattern_generation():
    action = LocalAIProvider().propose("generate marker 150 cm", "L")
    assert action["intent"] == "optimize_marker"
