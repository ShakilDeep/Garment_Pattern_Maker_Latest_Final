import json
from html import escape
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.application.service import NotReady
from app.infrastructure.marker_exports import marker_pdf, marker_svg


def export_svg(pattern):
    groups = []
    x, y, row_h = 5, 12, 0
    for p in pattern["pieces"]:
        if x + p["width"] > 160:
            x, y, row_h = 5, y + row_h + 12, 0
        points = " ".join(f"{a:.4f},{b:.4f}" for a, b in p.get("cut_points", p["points"]))
        grain = p["grainline"]
        groups.append(
            f'<g id="{escape(p["id"])}" transform="translate({x},{y})"><polygon points="{points}" fill="none" stroke="#17263a" stroke-width="0.25"/><line x1="{grain[0][0]}" y1="{grain[0][1]}" x2="{grain[1][0]}" y2="{grain[1][1]}" stroke="#17263a" stroke-width="0.2"/><text x="0" y="-2" font-size="2.5">{escape(p["name"])} / {pattern["size"]} / Cut {p["quantity"]}</text></g>'
        )
        x += p["width"] + 8
        row_h = max(row_h, p["height"])
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1700mm" height="{(y + row_h + 8) * 10}mm" viewBox="0 0 170 {y + row_h + 8}"><title>Demo shirt pattern; calibration required</title><metadata>{escape(json.dumps({"profile": pattern["profile"], "hash": pattern["input_hash"], "assumptions": pattern["assumptions"]}))}</metadata>{"".join(groups)}</svg>'


def export_pdf(p):
    output = BytesIO()
    c = Canvas(output, pagesize=(842, 595))
    c.setTitle("Garment Pattern Maker - Demo report")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(32, 558, "Garment Pattern Maker V5")
    c.setFont("Helvetica", 10)
    c.drawString(32, 537, f"{p['name'][:80]} / Size {p['pattern']['size']}")
    c.drawString(
        32, 520, "DEMO ONLY - Not production certified. Preview is not a full-scale cutting template."
    )
    x, y = 40, 480
    for piece in p["pattern"]["pieces"]:
        w, h = piece["width"], piece["height"]
        scale = min(150 / max(w, 1), 165 / max(h, 1))
        c.saveState()
        c.translate(x, y)
        c.scale(scale, -scale)
        path = c.beginPath()
        for i, (px, py) in enumerate(piece.get("cut_points", piece["points"])):
            (path.moveTo if i == 0 else path.lineTo)(px, py)
        path.close()
        c.setLineWidth(0.7 / scale)
        c.drawPath(path)
        c.restoreState()
        c.drawString(x, y - 183, f"{piece['name']} - Cut {piece['quantity']}")
        x += 195
        if x > 700:
            x, y = 40, y - 218
    c.showPage()
    c.setPageSize((595, 842))
    y = 800
    c.setFont("Helvetica-Bold", 16)
    c.drawString(32, y, "Validation and provenance")
    c.setFont("Helvetica", 9)
    for text in [
        p["pattern"]["profile"],
        "Input fingerprint: " + p["pattern"]["input_hash"],
        *["Source: " + d["filename"] + " / SHA-256: " + d["sha256"] for d in p["documents"]],
        *p["pattern"]["assumptions"],
        *[v["severity"] + ": " + v["message"] for v in p["pattern"]["validation"]],
    ]:
        import textwrap

        for line in textwrap.wrap(text, 100):
            if y < 48:
                c.showPage()
                c.setFont("Helvetica", 9)
                y = 800
            y -= 13
            c.drawString(32, y, line)
    c.save()
    return output.getvalue()


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
