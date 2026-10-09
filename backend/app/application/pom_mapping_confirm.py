"""Command: the user confirms a chart row's canonical key, or marks the row not used.

Values never change; only the row's key and mapping status do. A key held by another matched row is
refused (it would overwrite that row's drafting input), and nothing is modified when a check fails.
"""
from app.domain.pom_labels import normalize
from app.domain.pom_mapping import NOT_USED, UNMAPPED, UNMATCHED
from app.domain.pom_synonyms import canonical_keys

CONFIRMED = "confirmed"


def chart_row(project, row: int) -> dict:
    found = next((r for r in project["measurements"] if r.get("row") == row and "original_label" in r), None)
    if found is None:
        raise KeyError(f"POM row {row}")
    return found


def row_by_label(project, label: str) -> int:
    """The unmapped row whose source name matches ``label`` (case and spacing ignored)."""
    wanted = normalize(label)
    for row in project["measurements"]:
        if row.get("mapping_status") == UNMAPPED and normalize(row.get("original_label")) == wanted:
            return row["row"]
    raise ValueError(f"No unmapped row is named {label!r}")


def _check_free(project, target: dict, key: str) -> None:
    if key not in canonical_keys():
        raise ValueError("Unknown canonical measurement")
    for other in project["measurements"]:
        if other is not target and other["key"] == key and other.get("mapping_status") not in UNMATCHED:
            raise ValueError(f"{key} is already mapped to row {other.get('row')}")


def confirm(project, row: int, key: str | None) -> dict:
    """Map ``row`` to ``key``; ``None`` marks it not used (its key reverts to the source code)."""
    target = chart_row(project, row)
    if key is not None:
        _check_free(project, target, key)
    suggestion = project.get("mapping_suggestions", {}).pop(str(row), None)
    accepted = suggestion is not None and key is not None and suggestion.get("key") == key
    target.update(
        key=key or target["code"],
        mapping_status=CONFIRMED if key else NOT_USED,
        mapped_from=f"ai:{suggestion['provider']}" if accepted else "user",
    )
    return project
