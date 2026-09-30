from os import environ
from pathlib import Path
from uuid import uuid4

from app.application.errors import NotReady
from app.application.measurement_edits import history as edit_history
from app.application.measurement_edits import update_measurements as edit_measurements
from app.application.pattern_workflow import build as build_pattern
from app.application.pattern_workflow import clear as clear_pattern
from app.application.pattern_workflow import generate as generate_pattern
from app.application.pattern_workflow import grade as grade_sizes
from app.application.pattern_workflow import nest as nest_marker
from app.application.source_import import clear_sources, import_source

ROOT = Path(__file__).resolve().parents[3]


def demo_source_path(filename: str) -> Path:
    """Resolve demo workbook/PDF from env or shipped fixtures only (never references/)."""
    candidates = []
    env = Path(environ.get("DEMO_SOURCES_DIR", "") or "")
    if str(env):
        candidates.append(env / filename)
    candidates.append(ROOT / "fixtures" / "demo_sources" / filename)
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"Demo source {filename!r} is missing. Expected under fixtures/demo_sources."
    )


class Service:
    def __init__(self, repository):
        self.repo = repository

    def create(self, name, demo=False):
        p = {
            "id": str(uuid4()), "name": name, "measurements": [], "documents": [],
            "techpack": None, "resolutions": {}, "pattern": None, "pattern_history": [],
            "grades": [], "marker": None, "previous_marker": None, "audit": [],
            "state": "CREATED", "transitions": [], "undo": [], "redo": [],
        }
        if demo:
            self.import_data(p, "Book2(4).xlsx", demo_source_path("Book2(4).xlsx").read_bytes())
            self.import_data(p, "1078983(5).pdf", demo_source_path("1078983(5).pdf").read_bytes())
        return self.repo.save(p, "project_created")

    @staticmethod
    def _ensure_active(project):
        if project.get("archived") or project.get("state") == "ARCHIVED":
            raise NotReady("Project is archived; restore it before running this operation")

    def import_data(self, p, filename, data, replace=False):
        return import_source(self, p, filename, data, replace)

    def invalidate(self, p):
        if p["pattern"]:
            p["pattern"]["stale"] = True
        p["grades"] = []
        p["marker"] = None
        p["previous_marker"] = None

    def update_measurements(self, p, changes, size):
        return edit_measurements(self, p, changes, size)

    def history(self, p, direction):
        return edit_history(self, p, direction)

    def build(self, p, size, allowance=0):
        return build_pattern(p, size, allowance)

    def generate(self, p, size, allowance=0):
        return generate_pattern(self, p, size, allowance)

    def clear_pattern(self, p):
        return clear_pattern(self, p)

    def clear_sources(self, p):
        """Archive and remove imported sources so the same file can be imported again."""
        return clear_sources(self, p)

    def grade(self, p, sizes, allowance=None):
        return grade_sizes(self, p, sizes, allowance)

    def nest(self, p, size, width, quantity, gap, quantities=None, seed=0, time_budget_ms=250, iterations=1, grain_policy="vertical"):
        return nest_marker(self, p, size, width, quantity, gap, quantities, seed, time_budget_ms, iterations, grain_policy)
