"""T132: detection stores an editable proposal; only the user's confirmed choice becomes the style."""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.main import create_app
from app.domain.style_detect.proposal import parse_proposal
from app.domain.style_detect.schema import ALL_SPECS
from app.ports.ai_failure import ProviderFailure

SHIRT = {"garment": {"value": "shirt", "confidence": 0.97}, "sleeve": {"value": "short", "confidence": 0.9}}


class FakeDetector:
    name = "fake"

    def __init__(self, error=None):
        self.error, self.images = error, []

    def detect(self, image):
        self.images.append(image)
        if self.error:
            raise self.error
        return parse_proposal(SHIRT, "gemini", "gemini-test")


def _png():
    buffer = BytesIO()
    Image.new("RGB", (40, 20), "white").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def api(tmp_path):
    detector = FakeDetector()
    with TestClient(create_app(f"sqlite:///{tmp_path}/s.db", style_detector=detector)) as client:
        pid = client.post("/api/v1/projects", json={"name": "Style"}).json()["id"]
        yield client, f"/api/v1/projects/{pid}", detector


def test_the_option_table_is_served_for_manual_choice(api):
    client, _, _ = api
    table = client.get("/api/v1/style/options").json()
    assert [row["id"] for row in table] == [spec.id for spec in ALL_SPECS]
    assert table[0] == {"id": "garment", "label": "Garment type", "families": ["shirt", "pant"],
                        "choices": ["shirt", "pant", "unknown"], "note": ""}
    assert "side seam" in table[-1]["note"]


def test_detect_stores_the_proposal_then_the_users_choice_wins(api):
    client, base, detector = api
    found = client.post(base + "/style/detect", files={"file": ("flat.png", _png(), "image/png")}).json()
    assert detector.images[0].mime == "image/png"
    assert (found["proposal"]["garment"]["value"], found["proposal"]["provider"]) == ("shirt", "gemini")
    assert len(found["source_sha256"]) == 64 and found["page"] == 1
    body = {"garment": "shirt", "fit": "regular", "options": {"sleeve": "long", "collar": "shirt_collar"}}
    project = client.post(base + "/style/choices", json=body).json()
    choices = project["style_choices"]
    assert (choices["source"], choices["options"]["sleeve"], choices["options"]["yoke"]) == (
        "user", "long", "unknown")
    assert project["style_detection"]["proposal"]["model"] == "gemini-test"
    events = [entry["event"] for entry in project["audit"]]
    assert events[-2:] == ["style_detected", "style_confirmed"]
    assert project["audit"][-1]["details"]["changed"] == ["collar", "fit", "sleeve"]


@pytest.mark.parametrize(("body", "message"), [
    ({"garment": "shirt", "fit": "regular", "options": {"leg": "wide"}}, "leg"),
    ({"garment": "dress", "fit": "regular", "options": {}}, "garment"),
])
def test_an_invalid_choice_is_rejected_and_nothing_is_stored(api, body, message):
    client, base, _ = api
    response = client.post(base + "/style/choices", json=body)
    assert response.status_code == 400 and message in response.json()["message"]
    assert "style_choices" not in client.get(base).json()


@pytest.mark.parametrize(("name", "data", "status"), [
    ("notes.txt", b"plain text", 415), ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * 10_000_001, 413),
    ("broken.png", b"\x89PNG\r\n\x1a\nbroken", 400),
])
def test_bad_uploads_never_reach_the_detector(api, name, data, status):
    client, base, detector = api
    response = client.post(base + "/style/detect", files={"file": (name, data, "application/octet-stream")})
    assert response.status_code == status and detector.images == []


@pytest.mark.parametrize(("unavailable", "status", "code"), [(True, 503, "AI_UNAVAILABLE"),
                                                              (False, 502, "AI_OUTPUT_INVALID")])
def test_a_failing_detector_answers_with_the_ai_error_and_stores_nothing(tmp_path, unavailable, status, code):
    failing = FakeDetector(ProviderFailure("gemini", unavailable=unavailable))
    with TestClient(create_app(f"sqlite:///{tmp_path}/f.db", style_detector=failing)) as client:
        base = "/api/v1/projects/" + client.post("/api/v1/projects", json={"name": "F"}).json()["id"]
        before = client.get(base).json()["audit"]
        response = client.post(base + "/style/detect", files={"file": ("a.png", _png(), "image/png")})
        assert (response.status_code, response.json()["code"]) == (status, code)
        assert client.get(base).json()["audit"] == before
