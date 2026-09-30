from app.application.calibration import calibration_requirements
from app.application.requirement_resolve import resolve
from app.application.source_readiness import source_blockers
from app.domain.catalog import REQUIRED

__all__ = ["requirements", "resolve"]


def requirements(project, size="L"):
    answers = project["resolutions"]
    rows = {r["key"]: r for r in project["measurements"]}
    items = []

    def add(key, name, state, why, options, blocking=True):
        items.append(
            {
                "key": key,
                "name": name,
                "status": state,
                "blocking": blocking,
                "why": why,
                "options": options,
                "resolved": key in answers,
                "value": answers.get(key),
                "category": 'Measurements' if key.startswith('measurement:') else
                    'Drafting rules' if key == 'profile' else 'Source conflicts' if key in ('placket', 'fabric') else 'Review',
                "source": rows.get(key.removeprefix('measurement:'), {}).get('source', 'Project source files'),
                "confidence": None,
                "accepted_units": ['cm'] if key == 'units' or key.startswith('measurement:') else [],
                "question": why,
                "fallback_policy": 'Explicit demo default available' if key == 'profile' else 'No automatic default',
                "resolution": project.get('resolution_metadata', {}).get(key),
            }
        )

    add(
        "units",
        "Workbook units",
        "AVAILABLE" if "units" in answers else "AMBIGUOUS",
        "The workbook has no explicit unit column. Confirm its numeric values are centimeters.",
        ["cm"],
    )
    add(
        "profile",
        "Drafting profile",
        "AVAILABLE" if "profile" in answers else "DEMO_DEFAULT_AVAILABLE",
        "No client base block was supplied. Demo v1 uses documented geometric assumptions and needs production calibration.",
        ["demo_v1"],
    )
    add(
        "review",
        "Measurement review",
        "AVAILABLE" if "review" in answers else "MISSING",
        "Review the extracted values and confirm them before drafting.",
        ["confirmed"],
    )
    tech = project.get("techpack")
    if tech and tech.get("placket_cm") is not None and "front_placket_width" in rows:
        source = rows["front_placket_width"]["values"].get(size, {}).get("value")
        if source != tech["placket_cm"]:
            add(
                "placket",
                "Front placket source conflict",
                "AVAILABLE" if "placket" in answers else "CONFLICTING",
                f"Workbook: {source} cm. Tech pack: {tech['placket_cm']} cm (technical details). Choose the source for this demo.",
                ["workbook", "techpack"],
            )
    if tech and tech.get("fabric_conflict"):
        add(
            "fabric",
            "Fabric content needs client review",
            "CONFLICTING",
            "PDF page 4 text contains 97% cotton / 3% elastane and a 100% cotton table. Fabric physics and shrinkage are not modeled.",
            [],
            False,
        )
        if "fabric" in answers and answers["fabric"] == "not_applicable":
            items[-1]["status"] = "AVAILABLE"
            items[-1]["resolved"] = True
    for key in REQUIRED:
        value = rows.get(key, {}).get("values", {}).get(size, {}).get("value")
        if value is None or value <= 0:
            add(
                "measurement:" + key,
                key.replace("_", " ").title(),
                "MISSING",
                f"Enter a positive {size} value in cm in the measurement editor.",
                [],
            )
    items.extend(calibration_requirements(project))
    items.extend(source_blockers(project))
    return {
        "ready": not any(i["blocking"] and i["status"] != "AVAILABLE" for i in items),
        "items": items,
        "blockers": [i for i in items if i["blocking"] and i["status"] != "AVAILABLE"],
    }
