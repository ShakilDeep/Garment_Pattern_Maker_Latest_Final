"""Port: Strategy that proposes canonical keys for POM rows the synonym table could not map.

A suggestion is only a proposal; the user confirms it (``application/pom_mapping_confirm.py``).
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PomQuery:
    row: int
    code: str
    label: str
    alt_label: str | None = None


@dataclass(frozen=True)
class PomSuggestion:
    row: int
    key: str | None  # None: no confident proposal
    confidence: float
    provider: str
    reason: str


class PomSuggestError(Exception):
    """A provider failed (``unavailable``) or answered with output that could not be read."""

    def __init__(self, provider: str, *, unavailable: bool):
        self.provider, self.unavailable = provider, unavailable
        super().__init__(f"{provider} {'unavailable' if unavailable else 'returned invalid output'}")


class PomSuggester(Protocol):
    name: str

    def suggest(self, queries: Sequence[PomQuery], keys: Sequence[str]) -> list[PomSuggestion]:
        """One suggestion per query, each key drawn from ``keys``; raises PomSuggestError."""
        ...
