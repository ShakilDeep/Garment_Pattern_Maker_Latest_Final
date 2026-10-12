"""A project's Optitex export (T146): its stored V6 style as base DXF-AAMA + .RUL + all-sizes DXF + README.

Every chart size must be drafted; the accuracy gate runs before this (``accuracy/export_gate``). DXF-AAMA has
no cm unit, so a cm request writes METRIC (mm), as the single-size export does.
"""
from app.application.accuracy.project_report import accuracy_report
from app.application.accuracy.suites import profile_of
from app.application.errors import NotReady
from app.application.grading.aama_export import graded_files, zipped
from app.application.grading.aama_readme import readme
from app.application.project_style import project_style

AAMA_GRADED = "aama-graded"
ZIP = "application/zip"


def project_graded_aama(project: dict, unit: str) -> tuple[bytes, str]:
    """The zip and its file name."""
    style = project_style(project)
    if style is None:
        raise NotReady("Generate a current pattern before the Optitex export")
    missing = [size for size in style.sizes if not style.has_geometry(size)]
    if missing:
        raise NotReady(f"Grade every size before the Optitex export; missing {', '.join(missing)}")
    aama_unit = "inch" if unit == "inch" else "mm"
    files = graded_files(style, aama_unit)
    files["README.txt"] = readme(project, style, aama_unit, accuracy_report(project)["status"])
    return zipped(files), f"{profile_of(project)}_graded_aama.zip"
