"""Offline PomSuggester: fuzzy similarity between a row's names and the synonym table's names.

Thresholds match the assistant's terminology suggestions: a key is proposed only when it scores at least
``MIN_SCORE`` and beats the runner-up by ``MIN_MARGIN``; otherwise the row gets no key.
"""
import re
from collections.abc import Sequence
from difflib import SequenceMatcher

from app.domain.pom_labels import normalize
from app.domain.pom_synonyms import synonym_names
from app.ports.pom_suggester import PomQuery, PomSuggestion

MIN_SCORE = 0.82
MIN_MARGIN = 0.08
_NOISE = re.compile(r"[^A-Z0-9/À-ÿĀ-ž ]+")


def _comparable(name: str) -> str:
    return " ".join(_NOISE.sub(" ", normalize(name)).split())


class LocalPomSuggester:
    name = "local"

    def suggest(self, queries: Sequence[PomQuery], keys: Sequence[str]) -> list[PomSuggestion]:
        names = synonym_names()
        offered = {key: tuple(map(_comparable, names[key])) for key in keys if key in names}
        return [self._one(query, offered) for query in queries]

    def _one(self, query: PomQuery, offered: dict[str, tuple[str, ...]]) -> PomSuggestion:
        texts = [_comparable(text) for text in (query.label, query.alt_label) if text]
        ranked = sorted(
            ((max((self._score(text, name) for text in texts for name in names), default=0.0), key)
             for key, names in offered.items()),
            reverse=True,
        ) + [(0.0, ""), (0.0, "")]
        (score, key), (runner_up, _) = ranked[0], ranked[1]
        if score < MIN_SCORE or score - runner_up < MIN_MARGIN:
            return PomSuggestion(query.row, None, round(score, 3), self.name,
                                 "No confident match in the synonym table; choose the key manually.")
        return PomSuggestion(query.row, key, round(score, 3), self.name,
                             f"Name similarity {score:.0%} to a known name of {key} (not calibrated).")

    @staticmethod
    def _score(text: str, name: str) -> float:
        return SequenceMatcher(None, text, name).ratio()
