"""Grade from a specific pattern version using the inputs that version was drafted from."""
from copy import deepcopy

from app.application.pattern_inputs import version_view
from app.application.pattern_workflow import build_draft
from app.application.project_style import keep_named_drafts
from app.application.state import transition


def grade(service, p, sizes, allowance=None, source=None):
    service._ensure_active(p)
    base = source or p["pattern"]
    view = version_view(p, source) if source else p
    seam = allowance if allowance is not None else (base.get("seam_allowance", 0) if base else 0)
    drafts = {selected: build_draft(view, selected, seam) for selected in sizes}
    keep_named_drafts(p, drafts, (base or {}).get("size"))
    results = [draft.pattern for draft in drafts.values()]
    for result in results:
        result["graded_from"] = source["id"] if source else None
        if source and "sources" in source:
            result["sources"] = deepcopy(source["sources"])
    p["grades"] = results
    p["marker"] = None
    p["previous_marker"] = None
    transition(p, "GRADING_READY", "sizes_generated")
    service.repo.save(p, "sizes_generated", sizes)
    return results
