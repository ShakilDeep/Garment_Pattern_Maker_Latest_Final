"""StyleDetector over Gemini vision: the fixed schema goes out, the untrusted answer is parsed against it.

Only the prepared image (``image_prep``) and the option table are sent; no project data or measurements.
"""
import json

from app.domain.style_detect.proposal import StyleProposal, parse_proposal
from app.domain.style_detect.schema import ALL_SPECS, UNKNOWN, response_schema
from app.infrastructure.llm_clients import VisionCompletion
from app.ports.ai_failure import ProviderFailure
from app.ports.style_detector import StyleImage

INSTRUCTIONS = (
    "You classify a garment from one image: a photo or a technical flat sketch. For each option choose one "
    f'value from its list, or "{UNKNOWN}" when the image does not show it clearly; never guess. Give a '
    "confidence from 0 to 1 per option. Do not estimate any measurement."
)


def build_prompt() -> str:
    lines = [f"- {spec.id} ({spec.label}): {', '.join(spec.choices)}" + (f". {spec.note}" if spec.note else "")
             for spec in ALL_SPECS]
    return "\n".join([INSTRUCTIONS, "OPTIONS:", *lines])


class GeminiStyleDetector:
    name = "gemini"

    def __init__(self, complete: VisionCompletion, model: str):
        self._complete, self._model = complete, model

    def detect(self, image: StyleImage) -> StyleProposal:
        text = self._complete(build_prompt(), image, response_schema())
        try:
            return parse_proposal(json.loads(text), self.name, self._model)
        except ValueError:  # json.JSONDecodeError is a ValueError
            raise ProviderFailure(self.name, unavailable=False) from None
