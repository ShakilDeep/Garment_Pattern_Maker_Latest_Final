"""Chain of Responsibility over PomSuggesters: the first provider that answers wins.

Cloud failures are logged by provider name only (never the key or response text) and the next provider
takes over; the offline suggester is normally last, so the chain always answers.
"""
import logging
from collections.abc import Sequence

from app.ports.pom_suggester import PomQuery, PomSuggester, PomSuggestError, PomSuggestion

_LOG = logging.getLogger("garment")


class FallbackPomSuggester:
    name = "chain"

    def __init__(self, providers: Sequence[PomSuggester]):
        if not providers:
            raise ValueError("A suggester chain needs at least one provider")
        self._providers = tuple(providers)

    def suggest(self, queries: Sequence[PomQuery], keys: Sequence[str]) -> list[PomSuggestion]:
        *fallible, last = self._providers
        for provider in fallible:
            try:
                return provider.suggest(queries, keys)
            except PomSuggestError as failure:
                _LOG.warning("POM suggester %s failed (%s); trying the next provider", failure.provider,
                             "unavailable" if failure.unavailable else "invalid output")
        return last.suggest(queries, keys)  # its error, if any, is the caller's to handle
