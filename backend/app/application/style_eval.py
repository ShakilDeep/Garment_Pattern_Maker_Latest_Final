"""Score style detection against a labelled image set (doc 124: correct type and options, ≥30 per family).

An image is correct when its garment and every option its label states match; options the label leaves
out are not scored. A family's gate is ``open`` below ``MIN_PER_FAMILY`` images, ``pass`` when every image
is correct, and ``fail`` otherwise.
"""
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.domain.style_detect.proposal import StyleProposal
from app.domain.style_detect.schema import FAMILIES

MIN_PER_FAMILY = 30


@dataclass(frozen=True)
class Labelled:
    file: str
    garment: str
    options: Mapping[str, str]


def _misses(label: Labelled, proposal: StyleProposal) -> list[str]:
    if proposal.garment.value != label.garment:
        return ["garment"]
    found = {guess.id: guess.value for guess in (proposal.fit, *proposal.options)}
    return [key for key, value in label.options.items() if found.get(key) != value]


def _gate(images: int, correct: int) -> str:
    if images < MIN_PER_FAMILY:
        return "open"
    return "pass" if correct == images else "fail"


def evaluate(results: Iterable[tuple[Labelled, StyleProposal]]) -> dict[str, dict]:
    images, correct = Counter[str](), Counter[str]()
    misses: dict[str, Counter[str]] = {family: Counter() for family in FAMILIES}
    for label, proposal in results:
        missed = _misses(label, proposal)
        images[label.garment] += 1
        correct[label.garment] += not missed
        misses[label.garment].update(missed)
    return {family: {"images": images[family], "correct": correct[family],
                     "accuracy": round(correct[family] / images[family], 3) if images[family] else 0.0,
                     "gate": _gate(images[family], correct[family]), "misses": dict(misses[family])}
            for family in FAMILIES}
