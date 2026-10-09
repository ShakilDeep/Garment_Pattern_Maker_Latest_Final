"""Read model for the mapping screen: the imported chart's rows with their mapping state and suggestions."""
from app.application.errors import NotReady
from app.application.project_sizes import base_size
from app.domain.pom_synonyms import canonical_keys


def _row_view(row: dict, facts: dict, size: str, suggestion: dict | None) -> dict:
    fact = facts.get(str(row["row"]), {})
    return {
        "row": row["row"], "code": row["code"], "label": row["original_label"],
        "alt_label": fact.get("alt_label"), "key": row["key"], "status": row.get("mapping_status"),
        "mapped_from": row.get("mapped_from"), "half": bool(fact.get("half")), "tolerance": fact.get("tolerance"),
        "base_value": row["values"].get(size, {}).get("value"), "suggestion": suggestion,
    }


def chart_view(project) -> dict:
    chart = project.get("chart")
    if not chart:
        raise NotReady("Import a measurement chart before mapping its rows")
    base = base_size(project)
    shown = base or chart["sizes"][0]
    facts = {fact["ref"]: fact for fact in chart.get("rows", [])}
    suggestions = project.get("mapping_suggestions", {})
    return {
        "sizes": chart["sizes"], "base_size": base, "value_size": shown, "unit_hint": chart.get("unit_hint"),
        "canonical_keys": list(canonical_keys()),
        "rows": [_row_view(row, facts, shown, suggestions.get(str(row["row"])))
                 for row in project["measurements"] if "original_label" in row],
    }
