"""T132 acceptance: the 1078375 and CL1086464 tech-pack flats are classified (doc 124, build plan M5).

``recorded`` replays Gemini's real answer captured by scripts/record_style_detect.py; ``live`` asks Gemini
again and runs only when GEMINI_API_KEY is set.
Both need the local client tech packs (kept out of the public repo).
"""
import hashlib
import json
import os

import pytest
from conftest import REFERENCE_PATTERNS, needs_tech_packs

from app.domain.style_detect.schema import PROMPT_VERSION
from app.infrastructure.image_prep import prepare_image
from app.infrastructure.provider_factory import get_style_detector
from app.infrastructure.style_detect_gemini import GeminiStyleDetector

RECORDED = REFERENCE_PATTERNS.parent / "style_detect"
EXPECTED = {
    "1078375": {"garment": {"shirt"}, "collar": {"shirt_collar"}, "yoke": {"yes"}, "sleeve": {"short"}},
    "CL1086464": {"garment": {"pant"}, "leg": {"wide"}, "waistband": {"elastic", "elastic_drawcord"},
                  "pockets": {"cross"}},
}

# Owner, 2026-10-11: the CL1086464 pockets are cross pockets, the client's name for a slant pocket from the
# waist into the side seam (as cut in the 1074664 CROSS PKT PANT: diagonal FRONT corner + FACING1 strip).
CASES = list(EXPECTED)


def _image(style):
    return prepare_image((REFERENCE_PATTERNS / f"{style}.pdf").read_bytes(), 1)


def _assert_classified(style, proposal):
    found = {guess.id: guess.value for guess in (proposal.garment, *proposal.options)}
    for key, allowed in EXPECTED[style].items():
        assert found[key] in allowed, f"{style} {key}: {found[key]}"


@needs_tech_packs
@pytest.mark.parametrize("style", CASES)
def test_the_recorded_gemini_answer_classifies_the_flats(style):
    record = json.loads((RECORDED / f"{style}.json").read_text(encoding="utf-8"))
    image = _image(style)
    assert record["image_sha256"] == hashlib.sha256(image.data).hexdigest()
    assert record["prompt_version"] == PROMPT_VERSION
    detector = GeminiStyleDetector(lambda prompt, sent, schema: record["response"], record["model"])
    _assert_classified(style, detector.detect(image))


@needs_tech_packs
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="live Gemini check needs GEMINI_API_KEY")
@pytest.mark.parametrize("style", CASES)
def test_gemini_classifies_the_flats_live(style):
    _assert_classified(style, get_style_detector().detect(_image(style)))
