"""T126c: cloud POM suggesters join the chain only when their key is set; offline always comes last."""
import httpx

from app.infrastructure.provider_factory import get_pom_suggester
from app.ports.pom_suggester import PomQuery

QUERY = [PomQuery(4, "Q1", "1/2 WAIST AT TOP EGDE")]


def _client(seen):
    def handler(request):
        seen.append(request.url.host)
        return httpx.Response(503)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_without_keys_only_the_offline_suggester_answers():
    seen: list = []
    suggestion = get_pom_suggester({}, _client(seen)).suggest(QUERY, ["half_waist"])[0]
    assert (suggestion.provider, suggestion.key, seen) == ("local", "half_waist", [])


def test_gemini_then_groq_are_tried_before_falling_back_offline():
    seen: list = []
    env = {"GEMINI_API_KEY": "g", "GROQ_API_KEY": "q", "GROQ_MODEL": "custom-model"}
    suggestion = get_pom_suggester(env, _client(seen)).suggest(QUERY, ["half_waist"])[0]
    assert seen == ["generativelanguage.googleapis.com", "api.groq.com"]
    assert suggestion.provider == "local"


def test_an_empty_key_counts_as_unset():
    seen: list = []
    get_pom_suggester({"GEMINI_API_KEY": ""}, _client(seen)).suggest(QUERY, ["half_waist"])
    assert seen == []
