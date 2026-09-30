"""Conservative terminology suggestions. Never change measurements or convert their meaning."""

import re
from difflib import SequenceMatcher

from app.domain.catalog import MAPPING

ALIASES = {"shoulder breadth": "shoulder_point_to_point", "shoulder width": "shoulder_point_to_point"}


def suggest(text, context):
    match = re.fullmatch(r'map (?:measurement )?label\s+["\']?(.+?)["\']?', text)
    if not match:
        return None
    label = match[1].strip(" \"'")
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", label).split())
    options = {key: key.replace("_", " ") for key in MAPPING.values()}
    scores = {key: SequenceMatcher(None, normalized, value).ratio() for key, value in options.items()}
    for row in (context or {}).get("measurement_labels", []):
        if row["key"] in options and row.get("label"):
            source_label = " ".join(re.sub(r"[^a-z0-9]+", " ", row["label"].lower()).split())
            scores[row["key"]] = max(
                scores[row["key"]], SequenceMatcher(None, normalized, source_label).ratio()
            )
    if normalized in ALIASES:
        scores[ALIASES[normalized]] = 1.0
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    key, score = ranked[0]
    if score < 0.82 or score - ranked[1][1] < 0.08:
        return "No confident mapping. Review the source definition and choose a canonical measurement manually. No values changed."
    return (
        f"Suggested canonical key: {key}. Terminology similarity: {score:.0%} (not calibrated confidence). "
        "Review the source measurement method and units before accepting. No values or source labels changed."
    )
