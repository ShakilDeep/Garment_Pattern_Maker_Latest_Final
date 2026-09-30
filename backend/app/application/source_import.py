"""Source lifecycle use cases: import a workbook or tech pack, and clear imported sources."""
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.application.errors import NotReady
from app.application.state import ALLOWED, transition
from app.infrastructure.parsers import parse_pdf, parse_xlsx


def import_source(service, p, filename, data, replace=False):
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
    service.invalidate(p)


def clear_sources(service, p):
    """Archive and remove imported sources so the same file can be imported again."""
    service._ensure_active(p)
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
    service.repo.save(p, "sources_cleared")
    return p
