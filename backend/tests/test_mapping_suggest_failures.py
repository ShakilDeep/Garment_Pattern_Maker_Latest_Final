"""T126c: a suggester failure reaches the client as the stable AI error body and changes nothing."""
import pytest
from fastapi.testclient import TestClient
from test_mapping_routes import UNKNOWN, XLSX
from test_pom_mapping_confirm import Fake

from app.api.main import create_app
from app.ports.pom_suggester import PomSuggestError


@pytest.mark.parametrize(("unavailable", "status", "code"), [
    (True, 503, "AI_UNAVAILABLE"),
    (False, 502, "AI_OUTPUT_INVALID"),
])
def test_a_failing_suggester_answers_with_the_ai_error_and_stores_nothing(tmp_path, unavailable, status, code):
    failing = Fake(error=PomSuggestError("gemini", unavailable=unavailable))
    with TestClient(create_app(f"sqlite:///{tmp_path}/fail.db", pom_suggester=failing)) as client:
        pid = client.post("/api/v1/projects", json={"name": "Fail"}).json()["id"]
        base = f"/api/v1/projects/{pid}"
        client.post(base + "/documents", files={"file": ("c.xlsx", UNKNOWN, XLSX)})
        before = client.get(base).json()
        response = client.post(base + "/mappings/suggest")
        assert (response.status_code, response.json()["code"]) == (status, code)
        assert "gemini" not in response.json()["message"]
        after = client.get(base).json()
        assert after["measurements"] == before["measurements"]
        assert after["audit"] == before["audit"]
        assert client.get(base + "/chart").json()["rows"][1]["suggestion"] is None
