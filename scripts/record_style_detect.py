"""Send page 1 (the flats) of each client tech pack to Gemini once and record its raw answer (T132).

Usage: python scripts/record_style_detect.py
Needs GEMINI_API_KEY (environment or the repo-root .env). Writes fixtures/style_detect/<style>.json with the
model's text, the prepared image's sha256, the model and the prompt version; never the key.
"""
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.style_detect.schema import PROMPT_VERSION, response_schema
from app.infrastructure.image_prep import prepare_image
from app.infrastructure.llm_clients import gemini_vision
from app.infrastructure.provider_factory import DEFAULT_GEMINI_VISION_MODEL, VISION_TIMEOUT_S
from app.infrastructure.style_detect_gemini import build_prompt
from app.ports.ai_failure import ProviderFailure

SOURCES = {"1078375": "1078375.pdf", "CL1086464": "CL1086464.pdf"}
PAGE = 1
ATTEMPTS = 3
RETRY_WAIT_S = 10


def _key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "GEMINI_API_KEY" and value.strip():
            return value.strip().strip("\"'")
    raise SystemExit("GEMINI_API_KEY is not set")


def _status(response: httpx.Response) -> None:
    if response.is_error:  # the status only: the body may echo request details
        print(f"Gemini answered HTTP {response.status_code}")


def _ask(complete, image) -> str:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return complete(build_prompt(), image, response_schema())
        except ProviderFailure as failure:
            if not failure.unavailable or attempt == ATTEMPTS:
                raise
            time.sleep(RETRY_WAIT_S * attempt)
    raise AssertionError("unreachable")


def main() -> None:
    model = os.environ.get("GEMINI_VISION_MODEL", DEFAULT_GEMINI_VISION_MODEL)
    out = ROOT / "fixtures" / "style_detect"
    out.mkdir(exist_ok=True)
    with httpx.Client(timeout=VISION_TIMEOUT_S, event_hooks={"response": [_status]}) as client:
        complete = gemini_vision(client, _key(), model)
        for style, source in SOURCES.items():
            image = prepare_image((ROOT / "fixtures" / "reference_patterns" / source).read_bytes(), PAGE)
            record = {"style": style, "source": source, "page": PAGE, "model": model,
                      "prompt_version": PROMPT_VERSION,
                      "image_sha256": hashlib.sha256(image.data).hexdigest(),
                      "recorded_at": datetime.now(UTC).date().isoformat(),
                      "response": _ask(complete, image)}
            (out / f"{style}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            print(f"{style}: recorded {model} answer")


if __name__ == "__main__":
    main()
