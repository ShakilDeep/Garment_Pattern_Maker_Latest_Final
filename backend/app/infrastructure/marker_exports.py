import json
from html import escape
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas


def marker_svg(marker):
    shapes = []
    for index, placed in enumerate(marker['placements']):
        points = ' '.join(f"{x + placed['x']:.4f},{y + placed['y']:.4f}" for x, y in placed['points'])
        label = escape(f"{placed['name']} {placed.get('size', marker.get('size', ''))}")
        shapes.append(
            f'<g id="placement-{index}"><polygon points="{points}" fill="none" '
            f'stroke="#17263a" stroke-width="0.15"/><text x="{placed["x"] + 1}" '
            f'y="{placed["y"] + 3}" font-size="2">{label}</text></g>'
        )
    metadata = escape(json.dumps({
        'strategy': marker['strategy'], 'gap': marker['gap'], 'utilization': marker['utilization']
    }))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{marker["width"] * 10}mm" '
        f'height="{marker["length"] * 10}mm" viewBox="0 0 {marker["width"]} {marker["length"]}">'
        f'<title>Demo marker; calibration required</title><metadata>{metadata}</metadata>{"".join(shapes)}</svg>'
    )


def marker_pdf(project):
    marker = project['marker']
    output = BytesIO()
    canvas = Canvas(output, pagesize=(842, 595))
    canvas.setTitle('Garment Pattern Maker - Marker preview')
    canvas.setFont('Helvetica-Bold', 16)
    canvas.drawString(28, 565, 'Marker preview - demo only')
    scale = min(780 / marker['width'], 500 / marker['length'])
    for placed in marker['placements']:
        path = canvas.beginPath()
        for index, (x, y) in enumerate(placed['points']):
            px = 28 + (x + placed['x']) * scale
            py = 535 - (y + placed['y']) * scale
            (path.moveTo if index == 0 else path.lineTo)(px, py)
        path.close()
        canvas.drawPath(path)
    canvas.setFont('Helvetica', 9)
    footer = f"{marker['strategy']} / utilization {marker['utilization']:.2f}% / calibration required"
    canvas.drawString(28, 18, footer)
    canvas.save()
    return output.getvalue()
