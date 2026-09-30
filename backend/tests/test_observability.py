"""Structured request logs must include correlation, duration, and outcome."""
import json
import logging

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_health_log_includes_duration_use_case_and_request_id(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="garment")
    with TestClient(create_app(f"sqlite:///{tmp_path}/obs.db")) as client:
        response = client.get("/health")
    records = [json.loads(r.message) for r in caplog.records if r.name == "garment" and r.message.startswith("{")]
    payload = next(item for item in records if item.get("path") == "/health")
    assert payload["request_id"] == response.headers["x-request-id"]
    assert payload["use_case"]
    assert payload["duration_ms"] >= 0
    assert payload["outcome"] == "success"
    assert payload["status"] == 200
    assert "document" not in payload
    assert "secret" not in json.dumps(payload).lower()
