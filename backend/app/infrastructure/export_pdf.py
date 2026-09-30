"""Pattern PDF demo report: piece previews plus validation and provenance pages."""
import textwrap
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas


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
        for line in textwrap.wrap(text, 100):
            if y < 48:
                c.showPage()
                c.setFont("Helvetica", 9)
                y = 800
            y -= 13
            c.drawString(32, y, line)
    c.save()
    return output.getvalue()
