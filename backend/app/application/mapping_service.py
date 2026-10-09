"""Use-case facade for the mapping screen: chart view, AI suggestions and the user's confirmation."""
from copy import deepcopy

from app.application.chart_view import chart_view
from app.application.measurement_edits import commit_change
from app.application.pom_mapping_confirm import confirm
from app.application.pom_suggestions import suggest_mappings
from app.ports.pom_suggester import PomSuggester


def confirm_mapping(service, project, row: int, key: str | None):
    """Undoable: map ``row`` to ``key`` (``None`` = not used) and mark the pattern stale."""
    service._ensure_active(project)
    before = deepcopy(project["measurements"])
    confirm(project, row, key)
    return commit_change(service, project, before, "mapping_confirmed", {"row": row, "key": key})


class MappingService:
    def __init__(self, service, suggester: PomSuggester):
        self._service, self._suggester = service, suggester

    def chart(self, pid: str) -> dict:
        return chart_view(self._service.repo.get(pid))

    def suggest(self, pid: str) -> list[dict]:
        project = self._service.repo.get(pid)
        self._service._ensure_active(project)
        suggestions = suggest_mappings(project, self._suggester)
        if suggestions:
            providers = sorted({suggestion["provider"] for suggestion in suggestions})
            self._service.repo.save(project, "mapping_suggested",
                                    {"rows": [s["row"] for s in suggestions], "providers": providers})
        return suggestions

    def confirm(self, pid: str, row: int, key: str | None):
        return confirm_mapping(self._service, self._service.repo.get(pid), row, key)
