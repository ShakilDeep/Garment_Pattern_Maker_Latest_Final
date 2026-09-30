"""Bounded, detached evidence for assistance; no trusted geometry or project secrets."""

from copy import deepcopy

from app.application.requirements import requirements


def build_context(project, size, piece_id=None):
    candidates = [project.get("pattern"), *project.get("grades", [])]
    pattern = next((p for p in candidates if p and p["size"] == size), None)
    piece = None
    if piece_id is not None:
        piece = next((p for p in (pattern or {}).get("pieces", []) if p["id"] == piece_id), None)
        if piece is None:
            raise KeyError(piece_id)
    unresolved = [r for r in requirements(project, size)["items"] if r["status"] != "AVAILABLE"]
    issues = []
    labels = []
    for row in project["measurements"]:
        cell = row.get("values", {}).get(size, {})
        labels.append({k: row.get(k) for k in ("key", "label", "source", "source_id")})
        if cell.get("issue"):
            issues.append(
                {"label": row.get("label", row["key"]), "source": row.get("source"), "issue": cell["issue"]}
            )
    for attribute in (project.get("techpack") or {}).get("attributes", []):
        if attribute.get("confidence", 1) is not None and attribute.get("confidence", 1) < 0.8:
            issues.append(
                {
                    "label": attribute["key"],
                    "source": attribute.get("source"),
                    "page": attribute.get("page"),
                    "issue": "Extraction candidate needs source review",
                }
            )
    validation = [v for v in (pattern or {}).get("validation", []) if v.get("severity") != "PASS"]
    result = {
        "project_id": project["id"],
        "size": size,
        "requirements": [
            {k: r.get(k) for k in ("key", "name", "status", "blocking", "why", "source")}
            for r in unresolved[:50]
        ],
        "source_issues": issues[:50],
        "measurement_labels": labels[:100],
        "pattern": {k: pattern.get(k) for k in ("id", "size", "stale", "calibration")} if pattern else None,
        "validation": [
            {k: v.get(k) for k in ("severity", "code", "piece", "message", "action")} for v in validation[:50]
        ],
        "selected_piece": {k: piece.get(k) for k in ("id", "name", "width", "height", "quantity", "seams")}
        if piece
        else None,
        "truncated": len(unresolved) > 50 or len(issues) > 50 or len(labels) > 100 or len(validation) > 50,
    }
    return deepcopy(result)
