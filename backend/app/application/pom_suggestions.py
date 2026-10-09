"""Use case: ask a PomSuggester about the chart's unmapped rows and store its proposals, never applying them."""
from dataclasses import asdict
from datetime import UTC, datetime

from app.application.assistant_contracts import AssistantFailure
from app.domain.pom_mapping import UNMAPPED, UNMATCHED
from app.domain.pom_synonyms import canonical_keys
from app.ports.pom_suggester import PomQuery, PomSuggester, PomSuggestError


def chart_alt_labels(project) -> dict[str, str | None]:
    return {row["ref"]: row.get("alt_label") for row in (project.get("chart") or {}).get("rows", [])}


def unmapped_queries(project) -> list[PomQuery]:
    alt = chart_alt_labels(project)
    return [PomQuery(row["row"], row["code"], row["original_label"], alt.get(str(row["row"])))
            for row in project["measurements"] if row.get("mapping_status") == UNMAPPED]


def free_keys(project) -> list[str]:
    """Canonical keys no matched row holds yet, so a suggestion can never collide with one."""
    taken = {row["key"] for row in project["measurements"] if row.get("mapping_status") not in UNMATCHED}
    return [key for key in canonical_keys() if key not in taken]


def suggest_mappings(project, suggester: PomSuggester) -> list[dict]:
    queries = unmapped_queries(project)
    if not queries:
        return []
    try:
        suggestions = suggester.suggest(queries, free_keys(project))
    except PomSuggestError as failure:
        raise AssistantFailure(unavailable=failure.unavailable) from None
    stored = project.setdefault("mapping_suggestions", {})
    at = datetime.now(UTC).isoformat()
    for suggestion in suggestions:
        stored[str(suggestion.row)] = {**asdict(suggestion), "at": at}
    return [asdict(suggestion) for suggestion in suggestions]
