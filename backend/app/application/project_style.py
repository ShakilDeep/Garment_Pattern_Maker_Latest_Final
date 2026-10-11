"""A project's stored V6 style, kept in step with its V5 pattern and grades (T141a).

The style is the geometry the CAD tools and the Optitex export read. For a dict block it is derived from
the current pattern and the grades drafted from it, so a V5 edit can never leave it behind; a named
block's style is its own drafted V6 pieces (T141c) and is never re-derived from their V5 view. It is
recomputed only when the pattern or a grade changes (`STYLE_KEY` remembers which versions it was built
from), and removed when there is no current pattern. An archived project keeps its style untouched.
"""
from collections.abc import Mapping
from dataclasses import replace

from app.application.cad.style_from_project import current_patterns, style_from_project
from app.application.cad.style_ids import new_style_id
from app.application.drafting_engine import Draft
from app.application.errors import NotReady
from app.application.project_sizes import project_sizes
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style
from app.domain.pattern.style_codec import style_from_json, style_to_json
from app.infrastructure.v5_view.pattern_view import V6_SOURCE

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
    if pattern.get("geometry_source") == V6_SOURCE:
        return  # a named block's style is its drafted V6 pieces, stored when drafted; never re-derived
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


def keep_named_drafts(project: dict, drafts: Mapping[str, Draft], base_size: str | None) -> None:
    """Store a named block's drafted V6 pieces as the project's style (T141c). Generating starts a new
    style at the base size; grading keeps the base and replaces every graded size, as V5 replaces its
    grades. Dict-block drafts are left to `refresh_style`."""
    named_pattern = (project.get("pattern") or {}).get("geometry_source") == V6_SOURCE
    named = any(draft.allowances for draft in drafts.values()) if drafts else named_pattern
    if not named:
        return
    stored = project_style(project) if base_size not in drafts else None
    if base_size is None or (base_size not in drafts and stored is None):
        raise NotReady("Generate a current pattern before grading")
    allowances = stored.allowances if stored is not None else drafts[base_size].allowances
    base = drafts[base_size].pieces if stored is None else stored.view(base_size)
    style = Style(new_style_id(), project["name"], project_sizes(project), base_size,
                  {base_size: SizePieces.from_pieces(base)}, allowances)
    for size, result in drafts.items():
        style = style.with_pieces(size, result.pieces)
    project[STYLE] = style_to_json(style)
