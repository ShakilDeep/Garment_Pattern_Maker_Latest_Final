from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_security_headers_health_dependency_and_audit_correlation(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/trust.db")) as client:
        health = client.get("/health")
        assert health.json()["database"] == "ok"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'self'" in health.headers["content-security-policy"]
        created = client.post("/api/v1/projects", json={"name": "Trace"})
        request_id = created.headers["x-request-id"]
        UUID(request_id)
        assert created.json()["audit"][-1]["correlation_id"] == request_id


def test_upload_rejects_mismatched_file_signature(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/signature.db"))
    pid = client.post("/api/v1/projects", json={"name": "Signature"}).json()["id"]
    response = client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": ("fake.pdf", b"PK\x03\x04not-a-pdf", "application/pdf")},
    )
    assert response.status_code == 415
    assert "signature" in response.json()["message"].lower()


def test_cors_does_not_reflect_unlisted_origins(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/cors.db"))
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
