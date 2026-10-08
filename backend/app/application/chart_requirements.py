"""Missing Information from an imported chart: unmapped POM rows and an undetectable base size.

Both are non-blocking: the drafting profile's required measurements already block real gaps, unmapped
rows never reach drafting, and grading does not use the base size yet. Neither is ever guessed.
"""


def _item(key, name, status, why, options, project):
    answers = project.get("resolutions", {})
    return {
        "key": key, "name": name, "status": status, "blocking": False, "why": why, "options": options,
        "resolved": key in answers, "value": answers.get(key), "category": "Measurements",
        "source": "Imported measurement chart", "confidence": None, "accepted_units": [], "question": why,
        "fallback_policy": "No automatic default", "resolution": project.get("resolution_metadata", {}).get(key),
    }


def chart_items(project) -> list[dict]:
    chart = project.get("chart")
    if not chart:
        return []
    items = [
        _item(f"mapping:{row['row']}", row["original_label"], "MISSING",
              f"Row {row['row']} '{row['original_label']}' has no canonical measurement. "
              "Confirm a mapping or mark it not used.", [], project)
        for row in project.get("measurements", [])
        if row.get("mapping_status") == "unmapped"
    ]
    if chart.get("base_size") is None:
        sizes = list(chart.get("sizes", []))
        status = "AVAILABLE" if "base_size" in project.get("resolutions", {}) else "AMBIGUOUS"
        items.append(_item("base_size", "Base size", status,
                           "The workbook does not show which size is the base. Choose the base size.", sizes,
                           project))
    return items
