"""AI action trust: per-action parameter validation and local intent recognition."""
import pytest
from test_ai_trust import proposal, setup_client

from app.infrastructure.ai_provider import LocalAIProvider


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
