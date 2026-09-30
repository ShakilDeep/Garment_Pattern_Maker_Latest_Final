"""Command: record an explicit label-to-key mapping without changing values."""
from app.domain.catalog import MAPPING


def apply(project, source_label, canonical_key):
    if canonical_key not in set(MAPPING.values()):
        raise ValueError("Unknown canonical measurement")
    label = " ".join(source_label.lower().split())
    project.setdefault("accepted_mappings", {})[label] = canonical_key
    return project
