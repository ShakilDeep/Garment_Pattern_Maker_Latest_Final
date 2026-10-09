"""T126c: Gemini / Groq suggestions are untrusted; only known rows and keys survive, failures fall back."""
import json
import logging

import httpx
import pytest

from app.infrastructure.llm_clients import gemini_completion, groq_completion
from app.infrastructure.pom_suggest_chain import FallbackPomSuggester
from app.infrastructure.pom_suggest_llm import LlmPomSuggester
from app.infrastructure.pom_suggest_local import LocalPomSuggester
from app.ports.pom_suggester import PomQuery, PomSuggestError

SECRET = "test-key-not-real"
QUERIES = [PomQuery(5, "Q1", "1/2 HIPS"), PomQuery(6, "Q2", "1/2 WAIST AT TOP EGDE")]
KEYS = ("half_seat", "half_waist")
ANSWER = {"suggestions": [
    {"row": 5, "key": "half_seat", "confidence": 1.7, "reason": "hips = seat"},
    {"row": 6, "key": "made_up_key", "confidence": 0.9, "reason": "?"},
    {"row": 99, "key": "half_waist", "confidence": 0.9, "reason": "not asked"},
]}


def _gemini(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LlmPomSuggester("gemini", gemini_completion(client, SECRET, "gemini-test"))


def _gemini_body(text):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def test_gemini_keeps_only_asked_rows_and_offered_keys():
    seen = []
    suggester = _gemini(lambda request: seen.append(request) or _gemini_body(json.dumps(ANSWER)))
    first, second = suggester.suggest(QUERIES, KEYS)
    assert (first.row, first.key, first.confidence, first.provider) == (5, "half_seat", 1.0, "gemini")
    assert (second.row, second.key) == (6, None)
    assert seen[0].headers["x-goog-api-key"] == SECRET
    assert b"1/2 HIPS" in seen[0].content and b"half_seat" in seen[0].content


def test_groq_reads_the_chat_completion_message():
    def handler(request):
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        assert json.loads(request.content)["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(ANSWER)}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    suggester = LlmPomSuggester("groq", groq_completion(client, SECRET, "groq-test"))
    assert suggester.suggest(QUERIES, KEYS)[0].key == "half_seat"


@pytest.mark.parametrize("text", ["not json", '{"suggestions": "x"}', '[1, 2]', '{"suggestions": [{"row": "5"}]}'])
def test_unreadable_output_is_invalid_not_guessed(text):
    with pytest.raises(PomSuggestError) as raised:
        _gemini(lambda request: _gemini_body(text)).suggest(QUERIES, KEYS)
    assert raised.value.unavailable is False


def _timeout(request):
    raise httpx.ReadTimeout("slow", request=request)


@pytest.mark.parametrize(("handler", "unavailable"), [
    (lambda request: httpx.Response(429, json={"error": "quota"}), True),
    (_timeout, True),
    (lambda request: httpx.Response(200, json={"candidates": []}), False),
])
def test_http_failures_are_unavailable_and_bad_envelopes_invalid(handler, unavailable):
    with pytest.raises(PomSuggestError) as raised:
        _gemini(handler).suggest(QUERIES, KEYS)
    assert raised.value.unavailable is unavailable


def test_the_chain_falls_back_to_local_and_never_logs_the_key(caplog):
    failing = _gemini(lambda request: httpx.Response(500, text=SECRET))
    with caplog.at_level(logging.WARNING, logger="garment"):
        suggestions = FallbackPomSuggester([failing, LocalPomSuggester()]).suggest(QUERIES, KEYS)
    assert [s.provider for s in suggestions] == ["local", "local"]
    assert suggestions[1].key == "half_waist"
    assert "gemini" in caplog.text and SECRET not in caplog.text


def test_a_chain_whose_providers_all_fail_raises_the_last_error():
    failing = _gemini(lambda request: _gemini_body("nope"))
    with pytest.raises(PomSuggestError):
        FallbackPomSuggester([failing]).suggest(QUERIES, KEYS)


def test_no_queries_never_call_the_provider():
    assert _gemini(lambda request: pytest.fail("called")).suggest([], KEYS) == []
