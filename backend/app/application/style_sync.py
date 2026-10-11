"""Decorator over the project repository: every save keeps the project's stored style in step (T141a).

Pattern changes happen in many use cases (generate, grade, clear, measurement edits, V5 commands,
imports); refreshing the style at the one place they all end, the save, means none of them can forget it.
Everything else is delegated to the wrapped repository unchanged.
"""
from app.application.project_style import refresh_style


class StyleSyncRepository:
    def __init__(self, inner) -> None:
        self._inner = inner

    def save(self, project, event, details=None, artifact=None):
        refresh_style(project)
        return self._inner.save(project, event, details, artifact)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def style_synced(repository):
    return repository if isinstance(repository, StyleSyncRepository) else StyleSyncRepository(repository)
