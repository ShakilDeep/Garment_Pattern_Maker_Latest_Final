"""PomSuggester over any LLM completion (Gemini, Groq): builds the prompt and validates the untrusted answer.

Only row names and codes are sent, never measurement values. A suggestion survives only when its row was
asked for and its key was offered; every other row gets no key. Unreadable output is an error, not a guess.
"""
import json
from collections.abc import Sequence

from app.infrastructure.llm_clients import Completion
from app.ports.pom_suggester import PomQuery, PomSuggestError, PomSuggestion

INSTRUCTIONS = (
    "You map garment spec-sheet points of measure (POM) to canonical measurement keys. "
    "For each row choose one key from KEYS only when the row clearly measures the same thing; otherwise use "
    'null. Answer JSON only: {"suggestions": [{"row": <int>, "key": <string|null>, '
    '"confidence": <0..1>, "reason": <short string>}]}.'
)
MAX_REASON = 200


class LlmPomSuggester:
    def __init__(self, name: str, complete: Completion):
        self.name, self._complete = name, complete

    def suggest(self, queries: Sequence[PomQuery], keys: Sequence[str]) -> list[PomSuggestion]:
        if not queries:
            return []
        rows = [{"row": q.row, "code": q.code, "name": q.label, "alt_name": q.alt_label} for q in queries]
        prompt = f"{INSTRUCTIONS}\nKEYS: {json.dumps(list(keys))}\nROWS: {json.dumps(rows, ensure_ascii=False)}"
        answers = self._parse(self._complete(prompt), {q.row for q in queries}, set(keys))
        return [answers.get(q.row) or PomSuggestion(q.row, None, 0.0, self.name, "No suggestion.")
                for q in queries]

    def _parse(self, text: str, rows: set[int], keys: set[str]) -> dict[int, PomSuggestion]:
        try:
            items = json.loads(text)["suggestions"]
            if not isinstance(items, list):
                raise TypeError
            return {item["row"]: self._item(item) for item in items
                    if self._valid(item, rows) and item["key"] in keys}
        except (ValueError, KeyError, TypeError):
            raise PomSuggestError(self.name, unavailable=False) from None

    @staticmethod
    def _valid(item: dict, rows: set[int]) -> bool:
        if not isinstance(item["row"], int) or isinstance(item["row"], bool):
            raise TypeError("row must be an integer")
        return item["row"] in rows

    def _item(self, item: dict) -> PomSuggestion:
        confidence = float(item.get("confidence") or 0)
        reason = str(item.get("reason") or "")[:MAX_REASON]
        return PomSuggestion(item["row"], item["key"], round(min(max(confidence, 0.0), 1.0), 3), self.name, reason)
