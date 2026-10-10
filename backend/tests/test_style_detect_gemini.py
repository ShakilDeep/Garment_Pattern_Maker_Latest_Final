"""T132: the Gemini vision adapter sends the image and the fixed schema; its answer stays untrusted."""
import base64
import json

import httpx
import pytest

from app.domain.style_detect.schema import response_schema
from app.infrastructure.llm_clients import gemini_vision
from app.infrastructure.style_detect_gemini import GeminiStyleDetector
from app.ports.ai_failure import ProviderFailure
from app.ports.style_detector import StyleImage

SECRET = "test-key-not-real"
IMAGE = StyleImage("image/png", b"\x89PNG-fake")
ANSWER = {"garment": {"value": "pant", "confidence": 0.95}, "leg": {"value": "wide", "confidence": 0.8}}


def _detector(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiStyleDetector(gemini_vision(client, SECRET, "gemini-test"), "gemini-test")


def _body(text):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def test_the_request_carries_the_image_schema_and_key_header_only():
    seen = []
    proposal = _detector(lambda request: seen.append(request) or _body(json.dumps(ANSWER))).detect(IMAGE)
    sent = json.loads(seen[0].content)
    image, prompt = sent["contents"][0]["parts"]
    assert image["inlineData"] == {"mimeType": "image/png", "data": base64.b64encode(IMAGE.data).decode()}
    assert "garment" in prompt["text"] and SECRET not in seen[0].url.query.decode()
    assert sent["generationConfig"]["responseSchema"] == response_schema()
    assert seen[0].headers["x-goog-api-key"] == SECRET and SECRET not in seen[0].content.decode()
    assert (proposal.garment.value, proposal.provider, proposal.model) == ("pant", "gemini", "gemini-test")
    assert {guess.id: guess.value for guess in proposal.options}["leg"] == "wide"


@pytest.mark.parametrize(("response", "unavailable"), [
    (httpx.Response(500, text=SECRET), True),
    (_body("not json"), False),
    (_body(json.dumps({"garment": {"value": "dress", "confidence": 1}})), False),
    (httpx.Response(200, json={"candidates": []}), False),
])
def test_failures_are_provider_failures_without_the_response(response, unavailable):
    with pytest.raises(ProviderFailure) as caught:
        _detector(lambda request: response).detect(IMAGE)
    assert (caught.value.provider, caught.value.unavailable) == ("gemini", unavailable)
    assert SECRET not in str(caught.value)


def test_thought_parts_are_skipped_and_a_reply_without_an_answer_is_invalid():
    parts = [{"text": "thinking…", "thought": True}, {"text": json.dumps(ANSWER)}]
    reply = httpx.Response(200, json={"candidates": [{"content": {"parts": parts}}]})
    assert _detector(lambda request: reply).detect(IMAGE).garment.value == "pant"
    only_thought = httpx.Response(200, json={"candidates": [{"content": {"parts": parts[:1]}}]})
    with pytest.raises(ProviderFailure):
        _detector(lambda request: only_thought).detect(IMAGE)
