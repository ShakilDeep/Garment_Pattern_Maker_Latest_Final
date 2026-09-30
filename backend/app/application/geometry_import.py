"""Command: persist a validated geometry import onto a project snapshot."""
from copy import deepcopy

from app.application.state import transition


def persist_import(service, project, body):
    service._ensure_active(project)
    project["pattern"] = deepcopy(body.pattern)
    project["pattern"]["stale"] = False
    project["grades"] = deepcopy(body.grades)
    project["marker"] = deepcopy(body.marker)
    transition(project, "PATTERN_NEEDS_REVIEW", "geometry_imported")
    return service.repo.save(project, "geometry_imported", {"pattern_id": project["pattern"]["id"]})
