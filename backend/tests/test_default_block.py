"""A new project drafts with the client 1078375 block (owner, 2026-10-13): generating gives the seven PDS pieces,
from the block's PDS reference values once the user accepts them; nothing is drafted before that."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.domain.blocks.registry import demo_block

PDS_PIECES = [("FRT", 2), ("back", 1), ("back YK", 2), ("CLR", 2), ("BND TOP", 1), ("BND IN", 1), ("Sleeve", 2)]


@pytest.fixture
def demo(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/default.db")) as client:
        pid = client.post("/api/v1/projects", json={"name": "Default", "demo": True}).json()["id"]
        base = f"/api/v1/projects/{pid}"
        for key, value in (("units", "cm"), ("review", "confirmed"), ("placket", "workbook"),
                           ("profile", demo_block().id)):
            assert client.post(f"{base}/requirements/{key}/resolve", json={"value": value}).status_code == 200
        yield client, base


def _blockers(client, base) -> list[str]:
    return [item["key"] for item in client.get(f"{base}/requirements").json()["blockers"]]


def test_the_default_block_is_the_client_1078375_block(demo):
    client, _ = demo
    assert demo_block().id == "shirt_1078375"
    assert client.get("/health").json()["profile"] == "shirt_1078375"


def test_accepting_the_reference_values_drafts_the_seven_pds_pieces(demo):
    client, base = demo
    assert "block_reference" in _blockers(client, base)
    assert client.post(f"{base}/requirements/block_reference/resolve", json={"value": "accepted"}).status_code == 200
    generated = client.post(f"{base}/patterns/generate", json={"size": "L"})
    assert generated.status_code == 200, generated.text
    assert [(piece["name"], piece["quantity"]) for piece in generated.json()["pieces"]] == PDS_PIECES


def test_nothing_is_drafted_before_the_reference_values_are_accepted(demo):
    client, base = demo
    response = client.post(f"{base}/patterns/generate", json={"size": "L"})
    assert response.status_code == 409
    assert client.get(base).json()["pattern"] is None


def _generated_at_m(client, base):
    assert client.post(f"{base}/requirements/block_reference/resolve", json={"value": "accepted"}).status_code == 200
    assert client.post(f"{base}/patterns/generate", json={"size": "M", "allowance": 1}).status_code == 200


def test_a_pattern_based_at_m_is_compared_with_the_pds_at_its_own_base_size_l(demo):
    client, base = demo
    _generated_at_m(client, base)
    checks = client.get(f"{base}/accuracy").json()["checks"]
    assert [c["name"] for c in checks if not c["passed"] and c["gate"]] == ["PDS base size L drafted"]
    sizes = ["S", "M", "L", "XL", "XXL", "3XL"]
    assert client.post(f"{base}/grade", json={"sizes": sizes}).status_code == 200
    assert client.get(f"{base}/accuracy").json()["status"] == "ready"
    exported = client.get(f"{base}/exports/aama-graded?unit=mm")
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/zip"
