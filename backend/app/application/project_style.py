"""A project's stored V6 style, kept in step with its V5 pattern and grades (T141a).

The style is the geometry the CAD tools and the Optitex export read. For a dict block it is derived from
the current pattern and the grades drafted from it, so a V5 edit can never leave it behind. It is
recomputed only when the pattern or a grade changes (`STYLE_KEY` remembers which versions it was built
from), and removed when there is no current pattern. An archived project keeps its style untouched.
"""
from dataclasses import replace

from app.application.cad.style_from_project import current_patterns, style_from_project
from app.application.cad.style_ids import new_style_id
from app.domain.pattern.style import Style
from app.domain.pattern.style_codec import style_from_json, style_to_json

STYLE, STYLE_KEY = "style", "style_key"


def _source_key(project: dict) -> list:
    pattern = project["pattern"]
    grades = [[grade["id"], grade.get("graded_from"), bool(grade.get("stale"))] for grade in project["grades"]]
    return [pattern["id"], grades]  # every pattern change, V5 edits included, gets a new id


def refresh_style(project: dict) -> None:
    if project.get("archived") or project.get("state") == "ARCHIVED":
        return
    pattern = project.get("pattern")
    if not pattern or pattern.get("stale"):
        project.pop(STYLE, None)
        project.pop(STYLE_KEY, None)
        return
    key = _source_key(project)
    if project.get(STYLE_KEY) != key or STYLE not in project:
        project[STYLE] = style_to_json(style_from_project(project))
        project[STYLE_KEY] = key


def project_style(project: dict) -> Style | None:
    text = project.get(STYLE)
    return None if text is None else style_from_json(text)


def editable_style(project: dict) -> Style:
    """A new CAD style holding the project's geometry: the stored style when there is one (old projects
    fall back to a one-off conversion). It gets its own id, so a project can seed many CAD styles."""
    current_patterns(project)  # the same archived / current-pattern checks as the conversion
    stored = project_style(project)
    return style_from_project(project) if stored is None else replace(stored, id=new_style_id())
