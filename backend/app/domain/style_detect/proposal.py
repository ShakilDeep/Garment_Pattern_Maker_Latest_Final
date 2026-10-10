"""T132: parse a model's untrusted style proposal and check the user's confirmed choice against the table.

A proposal keeps only the options of its garment family; a missing option is ``unknown`` with confidence 0,
never guessed. A value outside the table, or a confidence that is not a number, rejects the whole answer.
"""
from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.style_detect.schema import (
    FAMILIES,
    FIT,
    GARMENT,
    PROMPT_VERSION,
    UNKNOWN,
    OptionSpec,
    options_for,
)


@dataclass(frozen=True)
class OptionGuess:
    id: str
    value: str
    confidence: float


@dataclass(frozen=True)
class StyleProposal:
    garment: OptionGuess
    fit: OptionGuess
    options: tuple[OptionGuess, ...]
    provider: str
    model: str
    prompt_version: str = PROMPT_VERSION


def _confidence(value: object, option_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Style option {option_id} has no numeric confidence")  # noqa: TRY004 - invalid output
    return round(min(max(float(value), 0.0), 1.0), 3)


def _guess(spec: OptionSpec, raw: Mapping) -> OptionGuess:
    item = raw.get(spec.id)
    if item is None:
        return OptionGuess(spec.id, UNKNOWN, 0.0)
    if not isinstance(item, Mapping) or item.get("value") not in spec.choices:
        raise ValueError(f"Style option {spec.id} is not one of {', '.join(spec.choices)}")
    return OptionGuess(spec.id, item["value"], _confidence(item.get("confidence"), spec.id))


def parse_proposal(raw: object, provider: str, model: str) -> StyleProposal:
    if not isinstance(raw, Mapping):
        raise ValueError("A style proposal must be a JSON object")  # noqa: TRY004 - invalid output
    garment = _guess(GARMENT, raw)
    options = tuple(_guess(spec, raw) for spec in options_for(garment.value))
    return StyleProposal(garment, _guess(FIT, raw), options, provider, model)


def _choice(spec: OptionSpec, value: str) -> str:
    if value not in spec.choices:
        raise ValueError(f"Style option {spec.id} cannot be {value}; choose {', '.join(spec.choices)}")
    return value


def validate_choices(garment: str, fit: str, options: Mapping[str, str]) -> dict:
    """The user's confirmed style: a known garment, its own options only, unset options ``unknown``."""
    if garment not in FAMILIES:
        raise ValueError(f"Style option garment must be {' or '.join(FAMILIES)}")
    specs = options_for(garment)
    foreign = sorted(set(options) - {spec.id for spec in specs})
    if foreign:
        raise ValueError(f"Style option {foreign[0]} does not apply to a {garment}")
    return {"garment": garment, "fit": _choice(FIT, fit),
            "options": {spec.id: _choice(spec, options.get(spec.id, UNKNOWN)) for spec in specs}}
