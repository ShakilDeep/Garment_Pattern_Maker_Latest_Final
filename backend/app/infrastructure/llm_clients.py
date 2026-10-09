"""Thin HTTP adapters for Gemini and Groq: prompt in, model text out (JSON mode requested).

Keys travel only in request headers; failures raise PomSuggestError without the response body or key.
"""
from collections.abc import Callable

import httpx

from app.ports.pom_suggester import PomSuggestError

Completion = Callable[[str], str]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _post(provider: str, client: httpx.Client, request: dict) -> dict:
    try:
        response = client.post(**request)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise PomSuggestError(provider, unavailable=True) from None


def _text(provider: str, body: dict, path: Callable[[dict], object]) -> str:
    try:
        text = path(body)
    except (KeyError, IndexError, TypeError):
        raise PomSuggestError(provider, unavailable=False) from None
    if not isinstance(text, str):
        raise PomSuggestError(provider, unavailable=False)
    return text


def gemini_completion(client: httpx.Client, api_key: str, model: str) -> Completion:
    def complete(prompt: str) -> str:
        body = _post("gemini", client, {
            "url": GEMINI_URL.format(model=model),
            "headers": {"x-goog-api-key": api_key},
            "json": {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {"responseMimeType": "application/json", "temperature": 0}},
        })
        return _text("gemini", body, lambda b: b["candidates"][0]["content"]["parts"][0]["text"])

    return complete


def groq_completion(client: httpx.Client, api_key: str, model: str) -> Completion:
    def complete(prompt: str) -> str:
        body = _post("groq", client, {
            "url": GROQ_URL,
            "headers": {"Authorization": f"Bearer {api_key}"},
            "json": {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                     "messages": [{"role": "user", "content": prompt}]},
        })
        return _text("groq", body, lambda b: b["choices"][0]["message"]["content"])

    return complete
