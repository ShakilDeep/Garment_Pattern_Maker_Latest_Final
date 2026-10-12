"""A project's accuracy report (T143): its stored style checked against its block's client reference.

The PDS checks take about a second for six sizes, so they are cached by content: the key is the style's
canonical JSON, and any edit, regrade or regeneration gives a new key. Chart checks read the project's
chart and run each time.
"""
from functools import lru_cache

from app.application.accuracy.chart_checks import chart_checks
from app.application.accuracy.model import Check
from app.application.accuracy.report_json import report_json
from app.application.accuracy.suites import SUITES, profile_of
from app.application.errors import NotReady
from app.application.project_style import STYLE
from app.domain.pattern.style import Style
from app.domain.pattern.style_codec import style_from_json, style_to_json
from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.reference_store import reference_for

CACHED_STYLES = 16


@lru_cache(maxsize=CACHED_STYLES)
def _pds_checks(block_id: str, style_text: str) -> tuple[Check, ...]:
    reference = reference_for(block_id)
    if reference is None:
        raise ValueError(f"Block {block_id} has no client reference")
    return tuple(SUITES[block_id].checks(style_from_json(style_text), reference))


def _style_text(project: dict, style: Style | None) -> str:
    if style is not None:
        return style_to_json(style)
    text = project.get(STYLE)
    if text is None:
        raise NotReady("Generate a current pattern before checking accuracy")
    return text


def _reference(project: dict) -> ReferenceStyle | None:
    profile = profile_of(project)
    return reference_for(profile) if profile in SUITES else None


def has_reference(project: dict) -> bool:
    return _reference(project) is not None


def accuracy_report(project: dict, style: Style | None = None) -> dict:
    """The report for ``style`` (default: the project's stored style); a CAD style passes its own geometry."""
    text = _style_text(project, style)
    checked = style if style is not None else style_from_json(text)
    reference = _reference(project)
    if reference is None:
        return report_json(project, checked, None, ())
    profile = profile_of(project)
    checks = (*_pds_checks(profile, text), *chart_checks(project, checked, SUITES[profile].definitions))
    return report_json(project, checked, reference.name, checks)
