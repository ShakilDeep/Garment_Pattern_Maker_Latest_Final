"""Thin HTTP adapters for Gemini and Groq: prompt (and image) in, model text out (JSON mode requested).

Keys travel only in request headers; failures raise ProviderFailure without the response body or key.
"""
import base64
from collections.abc import Callable

import httpx

from app.ports.ai_failure import ProviderFailure
from app.ports.style_detector import StyleImage

Completion = Callable[[str], str]
VisionCompletion = Callable[[str, StyleImage, dict], str]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def post_json(provider: str, client: httpx.Client, request: dict) -> dict:
    try:
        response = client.post(**request)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise ProviderFailure(provider, unavailable=True) from None


def response_text(provider: str, body: dict, path: Callable[[dict], object]) -> str:
    try:
        text = path(body)
    except (KeyError, IndexError, TypeError):
        raise ProviderFailure(provider, unavailable=False) from None
    if not isinstance(text, str):
        raise ProviderFailure(provider, unavailable=False)
    return text


def gemini_completion(client: httpx.Client, api_key: str, model: str) -> Completion:
    def complete(prompt: str) -> str:
        body = post_json("gemini", client, {
            "url": GEMINI_URL.format(model=model),
            "headers": {"x-goog-api-key": api_key},
            "json": {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {"responseMimeType": "application/json", "temperature": 0}},
        })
        return response_text("gemini", body, lambda b: b["candidates"][0]["content"]["parts"][0]["text"])

    return complete


def groq_completion(client: httpx.Client, api_key: str, model: str) -> Completion:
    def complete(prompt: str) -> str:
        body = post_json("groq", client, {
            "url": GROQ_URL,
            "headers": {"Authorization": f"Bearer {api_key}"},
            "json": {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                     "messages": [{"role": "user", "content": prompt}]},
        })
        return response_text("groq", body, lambda b: b["choices"][0]["message"]["content"])

    return complete


def _answer_part(body: dict) -> object:
    """A thinking model may send thought parts first; the answer is the first non-thought text part."""
    parts = body["candidates"][0]["content"]["parts"]
    return next((part["text"] for part in parts if "text" in part and not part.get("thought")), None)


def gemini_vision(client: httpx.Client, api_key: str, model: str) -> VisionCompletion:
    """One image plus instructions; ``schema`` is Gemini's ``responseSchema`` for structured output."""
    def complete(prompt: str, image: StyleImage, schema: dict) -> str:
        inline = {"mimeType": image.mime, "data": base64.b64encode(image.data).decode("ascii")}
        body = post_json("gemini", client, {
            "url": GEMINI_URL.format(model=model),
            "headers": {"x-goog-api-key": api_key},
            "json": {"contents": [{"parts": [{"inlineData": inline}, {"text": prompt}]}],
                     "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema,
                                          "temperature": 0}},
        })
        return response_text("gemini", body, _answer_part)

    return complete
