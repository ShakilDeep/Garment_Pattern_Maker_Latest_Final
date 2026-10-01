"""Single version-selection rule: a graded size wins over the base pattern (mirrored by frontend versionSelect.ts)."""


def select_for_size(project, size):
    graded = next((grade for grade in project.get("grades") or [] if grade.get("size") == size), None)
    if graded is not None:
        return graded
    base = project.get("pattern")
    return base if base and base.get("size") == size else None
