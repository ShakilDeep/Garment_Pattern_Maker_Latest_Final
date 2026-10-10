"""T132: Gemini reads images only when its key is set; otherwise the offline detector asks the user."""
import httpx
import pytest

from app.infrastructure.provider_factory import get_style_detector
from app.ports.ai_failure import ProviderFailure
from app.ports.style_detector import StyleImage

IMAGE = StyleImage("image/png", b"png")


def _client(seen):
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(503)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_without_a_key_nothing_is_sent_and_every_option_is_unknown():
    seen: list = []
    proposal = get_style_detector({"GROQ_API_KEY": "q"}, _client(seen)).detect(IMAGE)
    assert (proposal.provider, seen) == ("local", [])
    assert {guess.value for guess in (proposal.garment, proposal.fit, *proposal.options)} == {"unknown"}


def test_with_a_key_gemini_is_asked_with_the_vision_model_and_its_failure_is_not_hidden():
    seen: list = []
    detector = get_style_detector({"GEMINI_API_KEY": "g", "GEMINI_VISION_MODEL": "vision-x"}, _client(seen))
    with pytest.raises(ProviderFailure) as caught:
        detector.detect(IMAGE)
    assert caught.value.unavailable and seen == [
        "https://generativelanguage.googleapis.com/v1beta/models/vision-x:generateContent"]
