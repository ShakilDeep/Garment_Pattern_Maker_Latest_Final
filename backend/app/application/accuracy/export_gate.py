"""Export gate (T143, Guard): a style with accuracy errors is not exported in a geometry format (409).

Only a block with a client reference is checked; a project without a current style is left to the export's
own "generate first" refusal. The JSON backup and the marker exports are not geometry exports.
"""
from app.application.accuracy.project_report import accuracy_report, has_reference
from app.application.errors import NotReady
from app.application.project_style import STYLE
from app.domain.pattern.style import Style

GEOMETRY_KINDS = frozenset({"svg", "pdf", "dxf", "dxf-aama"})
SHOWN_ERRORS = 20  # details list the first failed checks; the report has them all


class AccuracyErrors(NotReady):
    """Accuracy errors block the export (409 ACCURACY_ERRORS); ``details`` lists the failed checks."""

    code = "ACCURACY_ERRORS"

    def __init__(self, failed: list[dict]):
        super().__init__(f"{len(failed)} accuracy errors block export; see GET /accuracy for the report")
        self.details = failed[:SHOWN_ERRORS]


def require_accurate(project: dict, style: Style | None = None) -> None:
    if not has_reference(project) or (style is None and project.get(STYLE) is None):
        return
    report = accuracy_report(project, style)
    failed = [check for check in report["checks"] if check["gate"] and not check["passed"]]
    if failed:
        raise AccuracyErrors(failed)


def accuracy_blocker(project: dict) -> bool:
    """True when the project's stored style has accuracy errors (readiness shows it before an export)."""
    try:
        require_accurate(project)
    except AccuracyErrors:
        return True
    return False
