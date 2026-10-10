"""Use cases (T132): store a detector's style proposal, then the user's confirmed choice, which always wins.

Neither touches measurements, geometry or the workflow state; a failed detection stores nothing.
"""
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256

from app.application.assistant_contracts import AssistantFailure
from app.domain.style_detect.proposal import StyleProposal, validate_choices
from app.ports.ai_failure import ProviderFailure
from app.ports.style_detector import StyleDetector, StyleImage


def _now() -> str:
    return datetime.now(UTC).isoformat()


def detect_style(project: dict, image: StyleImage, detector: StyleDetector, source: bytes, page: int) -> dict:
    try:
        proposal: StyleProposal = detector.detect(image)
    except ProviderFailure as failure:
        raise AssistantFailure(unavailable=failure.unavailable) from None
    project["style_detection"] = {"proposal": asdict(proposal), "source_sha256": sha256(source).hexdigest(),
                                  "page": page, "at": _now()}
    return project["style_detection"]


def _proposed(project: dict) -> dict[str, str]:
    proposal = (project.get("style_detection") or {}).get("proposal")
    if not proposal:
        return {}
    guesses = [proposal["garment"], proposal["fit"], *proposal["options"]]
    return {guess["id"]: guess["value"] for guess in guesses}


def confirm_style(project: dict, garment: str, fit: str, options: dict[str, str]) -> list[str]:
    """Store the user's style; returns the option ids where it differs from the stored proposal."""
    choices = validate_choices(garment, fit, options)
    chosen = {"garment": garment, "fit": choices["fit"], **choices["options"]}
    proposed = _proposed(project)
    project["style_choices"] = {**choices, "source": "user", "at": _now()}
    return sorted(key for key, value in chosen.items() if proposed.get(key, "unknown") != value)
