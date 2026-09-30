from datetime import UTC, datetime
from hashlib import sha256
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
from app.application.state import ALLOWED, transition
from app.infrastructure.parsers import parse_pdf, parse_xlsx

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
        digest = sha256(data).hexdigest()
        replacement_at = datetime.now(UTC).isoformat()
        if any(d["sha256"] == digest for d in p["documents"]) and not replace:
            raise NotReady("This document has already been imported")
        if filename.lower().endswith(".xlsx"):
            if p["measurements"] and not replace:
                raise NotReady(
                    "This project already has measurements. Create a new project to import a replacement without overwriting reviewed values."
                )
            if p["measurements"]:
                p.setdefault("measurement_versions", []).append({
                    "documents": list(p.get("documents", [])), "measurements": p["measurements"],
                    "replaced_at": replacement_at})
            p["measurements"] = parse_xlsx(data, filename)
        elif filename.lower().endswith(".pdf"):
            if p["techpack"] and not replace:
                raise NotReady("This project already has a tech pack. Create a new project to compare another source.")
            if p["techpack"]:
                p.setdefault("techpack_versions", []).append(p["techpack"])
            p["techpack"] = parse_pdf(data, filename)
        else:
            raise ValueError("Only XLSX and PDF files are supported")
        source_id = str(uuid4())
        parser_version = "xlsx_v2" if filename.lower().endswith(".xlsx") else p["techpack"]["parser"]
        p["documents"].append({"id": source_id, "filename": filename, "sha256": digest, "bytes": len(data),
                               "parser_version": parser_version, "imported_at": datetime.now(UTC).isoformat()})
        rows = p["measurements"] if filename.lower().endswith(".xlsx") else p["techpack"]["attributes"]
        for row in rows:
            row["source_id"] = source_id
        p["resolutions"].pop("review", None)
        if p.get("state", "CREATED") == "CREATED":
            transition(p, "SOURCES_UPLOADED", "source_uploaded")
        transition(p, "NEEDS_INPUT", "extraction_review_needed")
        self.invalidate(p)

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
        self._ensure_active(p)
        replaced_at = datetime.now(UTC).isoformat()
        if p.get("measurements") or p.get("documents"):
            p.setdefault("measurement_versions", []).append({
                "documents": list(p.get("documents", [])),
                "measurements": list(p.get("measurements", [])),
                "replaced_at": replaced_at,
            })
        if p.get("techpack"):
            p.setdefault("techpack_versions", []).append(p["techpack"])
        p["measurements"] = []
        p["documents"] = []
        p["techpack"] = None
        p["resolutions"] = {}
        if p.get("pattern"):
            p.setdefault("pattern_history", []).append(p["pattern"])
        p["pattern"] = None
        p["grades"] = []
        p["marker"] = None
        p["previous_marker"] = None
        state = p.get("state", "CREATED")
        if "NEEDS_INPUT" in ALLOWED.get(state, set()):
            transition(p, "NEEDS_INPUT", "sources_cleared")
        self.repo.save(p, "sources_cleared")
        return p

    def grade(self, p, sizes, allowance=None):
        return grade_sizes(self, p, sizes, allowance)

    def nest(self, p, size, width, quantity, gap, quantities=None, seed=0, time_budget_ms=250, iterations=1, grain_policy="vertical"):
        return nest_marker(self, p, size, width, quantity, gap, quantities, seed, time_budget_ms, iterations, grain_policy)
