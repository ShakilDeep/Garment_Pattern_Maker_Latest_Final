"""Explicit project workflow transitions with durable in-project history."""

from datetime import UTC, datetime

ALLOWED = {
    "CREATED": {"SOURCES_UPLOADED", "PATTERN_NEEDS_REVIEW"},
    "SOURCES_UPLOADED": {"EXTRACTION_IN_PROGRESS", "NEEDS_INPUT"},
    "EXTRACTION_IN_PROGRESS": {"NEEDS_INPUT", "MEASUREMENTS_READY"},
    "NEEDS_INPUT": {"MEASUREMENTS_READY"},
    "MEASUREMENTS_READY": {"PATTERN_NEEDS_REVIEW", "NEEDS_INPUT"},
    "PATTERN_NEEDS_REVIEW": {"PATTERN_READY", "GRADING_READY", "MARKER_READY", "EXPORT_READY", "MEASUREMENTS_READY", "NEEDS_INPUT"},
    "PATTERN_READY": {"PATTERN_NEEDS_REVIEW", "GRADING_READY", "MARKER_READY", "EXPORT_READY", "MEASUREMENTS_READY", "NEEDS_INPUT"},
    "GRADING_READY": {"PATTERN_NEEDS_REVIEW", "MARKER_READY", "EXPORT_READY", "MEASUREMENTS_READY", "NEEDS_INPUT"},
    "MARKER_READY": {"PATTERN_NEEDS_REVIEW", "GRADING_READY", "EXPORT_READY", "MEASUREMENTS_READY", "NEEDS_INPUT"},
    "EXPORT_READY": {"PATTERN_NEEDS_REVIEW", "GRADING_READY", "MARKER_READY", "DEMO_COMPLETE", "MEASUREMENTS_READY", "NEEDS_INPUT"},
    "DEMO_COMPLETE": {"PATTERN_NEEDS_REVIEW", "GRADING_READY", "MARKER_READY", "EXPORT_READY", "MEASUREMENTS_READY", "NEEDS_INPUT"},
}


def transition(project, target, reason, actor="system"):
    """Move a project to an allowed state and record why it moved."""
    current = project.get("state", "CREATED")
    if target == current:
        return project
    if target not in ALLOWED.get(current, set()):
        raise ValueError(f"Project cannot move from {current} to {target}")
    event = {
        "from": current,
        "to": target,
        "reason": reason,
        "actor": actor,
        "at": datetime.now(UTC).isoformat(),
    }
    project.setdefault("transitions", []).append(event)
    project["state"] = target
    return project
