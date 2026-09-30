"""Constructor-injected assistant provider selection. Cloud is optional."""
import os

from app.infrastructure.ai_provider import LocalAIProvider


def get_ai_provider():
    os.getenv("GARMENT_CLOUD_AI_KEY")
    return LocalAIProvider()
