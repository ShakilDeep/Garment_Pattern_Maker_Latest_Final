"""Assistant API receives only the current project's detached context."""
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.ai_provider import LocalAIProvider


def test_api_passes_only_current_project_context(tmp_path):
    class ContextProvider(LocalAIProvider):
        def propose(self, prompt, size, *, context=None):
            assert context["project_id"] == pid
            assert "audit" not in context
            return super().propose(prompt, size, context=context)

    client = TestClient(create_app(f"sqlite:///{tmp_path}/context.db", ai_provider=ContextProvider()))
    pid = client.post("/api/v1/projects", json={"name": "Context"}).json()["id"]
    response = client.post(
        f"/api/v1/projects/{pid}/assistant/propose", json={"prompt": "Explain requirements"}
    )
    assert response.status_code == 200
    assert "Workbook units" in response.json()["parameters"]["answer"]
    before = client.get(f"/api/v1/projects/{pid}").json()
    invalid = client.post(
        f"/api/v1/projects/{pid}/assistant/propose",
        json={"prompt": "Explain selected piece", "piece_id": "from-another-project"},
    )
    assert invalid.status_code == 404
    assert client.get(f"/api/v1/projects/{pid}").json() == before
