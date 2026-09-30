import json

from app.application.service import NotReady
from app.infrastructure.export_pdf import export_pdf
from app.infrastructure.export_svg import export_svg
from app.infrastructure.marker_exports import marker_pdf, marker_svg

__all__ = ["export_artifact", "export_pdf", "export_svg"]


def export_artifact(p, kind, size=None):
    if size is not None and kind not in ("marker-svg", "marker-pdf"):
        selected = next((g for g in p['grades'] if g['size'] == size), None)
        if selected is None and p['pattern'] and p['pattern']['size'] == size:
            selected = p['pattern']
        if selected is None:
            raise NotReady(f'Generate size {size} before exporting')
        p = {**p, 'pattern': selected}
    if kind in ("marker-svg", "marker-pdf"):
        if not p.get("marker"):
            raise NotReady("Generate a marker before exporting it")
        if kind == "marker-svg":
            return marker_svg(p["marker"]).encode(), "image/svg+xml"
        return marker_pdf(p), "application/pdf"
    if not p["pattern"] or p["pattern"].get("stale"):
        raise NotReady("Generate a current pattern before exporting")
    if any(v["severity"] == "ERROR" for v in p["pattern"]["validation"]):
        raise NotReady("Resolve geometry errors before export")
    if kind == "svg":
        return export_svg(p["pattern"]).encode(), "image/svg+xml"
    if kind == "pdf":
        return export_pdf(p), "application/pdf"
    if kind == "json":
        return json.dumps(
            {
                "schema_version": 1,
                "project": p["name"],
                "pattern": p["pattern"],
                "grades": p["grades"],
                "marker": p["marker"],
                "audit": p["audit"],
            },
            indent=2,
        ).encode(), "application/json"
    raise ValueError("Supported exports: SVG, PDF, JSON, marker SVG, marker PDF")
