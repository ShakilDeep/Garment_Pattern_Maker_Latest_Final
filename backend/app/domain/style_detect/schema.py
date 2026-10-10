"""T132: the fixed style-option vocabulary an image may propose (build plan M5); one table for every use.

Values are classification labels only. No option carries a measurement or geometry (doc 90): the 3.5 cm
placket width, for example, comes from the tech pack, never from the image. Every option ends with
``unknown`` so a model is never forced to guess.
"""
from dataclasses import dataclass

PROMPT_VERSION = "style_detect_v2"  # v2: pocket choices defined (owner, 2026-10-11)
UNKNOWN = "unknown"
FAMILIES = ("shirt", "pant")
_BOTH = FAMILIES


@dataclass(frozen=True)
class OptionSpec:
    id: str
    label: str
    families: tuple[str, ...]
    choices: tuple[str, ...]
    note: str = ""  # how to tell the choices apart, sent with the prompt


def _spec(option_id: str, label: str, families: tuple[str, ...], *choices: str, note: str = "") -> OptionSpec:
    return OptionSpec(option_id, label, families, (*choices, UNKNOWN), note)


GARMENT = _spec("garment", "Garment type", _BOTH, *FAMILIES)
FIT = _spec("fit", "Fit", _BOTH, "slim", "regular", "relaxed", "oversized")
OPTIONS = (
    _spec("collar", "Collar", ("shirt",), "none", "band", "shirt_collar"),
    _spec("placket", "Front placket", ("shirt",), "none", "full", "half"),
    _spec("yoke", "Back yoke", ("shirt",), "yes", "no"),
    _spec("sleeve", "Sleeve", ("shirt",), "short", "long"),
    _spec("leg", "Leg", ("pant",), "straight", "wide", "tapered"),
    _spec("waistband", "Waistband", ("pant",), "fixed", "elastic", "drawcord", "elastic_drawcord"),
    _spec("pockets", "Pockets", _BOTH, "none", "side_seam", "patch", "cross", note=(
        "side_seam: the opening runs along the side seam, straight or slightly angled; patch: sewn on top "
        "of the panel; cross: a clearly diagonal opening cut across the front panel, away from the side seam")),
)
ALL_SPECS = (GARMENT, FIT, *OPTIONS)


def options_for(garment: str) -> tuple[OptionSpec, ...]:
    """The options a garment family has; an unknown garment is asked every option."""
    return tuple(spec for spec in OPTIONS if garment == UNKNOWN or garment in spec.families)


def response_schema() -> dict:
    """Gemini ``responseSchema`` (OpenAPI subset): one ``{value, confidence}`` object per option."""
    def guess(spec: OptionSpec) -> dict:
        return {"type": "OBJECT", "required": ["value", "confidence"], "properties": {
            "value": {"type": "STRING", "enum": list(spec.choices)},
            "confidence": {"type": "NUMBER"}}}

    return {"type": "OBJECT", "required": [spec.id for spec in ALL_SPECS],
            "properties": {spec.id: guess(spec) for spec in ALL_SPECS}}
