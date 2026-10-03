"""Pattern SVG export: pieces laid out on a strip with grainlines, labels and metadata."""
import json
from html import escape

from app.infrastructure.piece_layout import strip_layout


def export_svg(pattern):
    groups = []
    placed, height = strip_layout(pattern["pieces"])
    for p, x, y in placed:
        points = " ".join(f"{a:.4f},{b:.4f}" for a, b in p.get("cut_points", p["points"]))
        grain = p["grainline"]
        groups.append(
            f'<g id="{escape(p["id"])}" transform="translate({x},{y})"><polygon points="{points}" fill="none" stroke="#17263a" stroke-width="0.25"/><line x1="{grain[0][0]}" y1="{grain[0][1]}" x2="{grain[1][0]}" y2="{grain[1][1]}" stroke="#17263a" stroke-width="0.2"/><text x="0" y="-2" font-size="2.5">{escape(p["name"])} / {pattern["size"]} / Cut {p["quantity"]}</text></g>'
        )
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1700mm" height="{height * 10}mm" viewBox="0 0 170 {height}"><title>Demo shirt pattern; calibration required</title><metadata>{escape(json.dumps({"profile": pattern["profile"], "hash": pattern["input_hash"], "assumptions": pattern["assumptions"]}))}</metadata>{"".join(groups)}</svg>'
