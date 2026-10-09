"""Constructor-injected AI provider selection. Cloud providers are optional; offline always works."""
import os
from collections.abc import Mapping

import httpx

from app.infrastructure.ai_provider import LocalAIProvider
from app.infrastructure.llm_clients import gemini_completion, groq_completion
from app.infrastructure.pom_suggest_chain import FallbackPomSuggester
from app.infrastructure.pom_suggest_llm import LlmPomSuggester
from app.infrastructure.pom_suggest_local import LocalPomSuggester

CLOUD_TIMEOUT_S = 15.0
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def get_ai_provider():
    return LocalAIProvider()


def get_pom_suggester(env: Mapping[str, str] | None = None, client: httpx.Client | None = None):
    """Gemini, then Groq (each only when its key is set), then the offline suggester."""
    env = os.environ if env is None else env
    providers: list = []
    cloud = [("gemini", "GEMINI", gemini_completion, DEFAULT_GEMINI_MODEL),
             ("groq", "GROQ", groq_completion, DEFAULT_GROQ_MODEL)]
    for name, prefix, completion, model in cloud:
        key = env.get(f"{prefix}_API_KEY")
        if key:
            client = client or httpx.Client(timeout=CLOUD_TIMEOUT_S)
            providers.append(LlmPomSuggester(name, completion(client, key, env.get(f"{prefix}_MODEL", model))))
    return FallbackPomSuggester([*providers, LocalPomSuggester()])
