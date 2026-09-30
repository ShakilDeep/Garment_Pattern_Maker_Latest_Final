"""Pattern SVG export: pieces laid out on a strip with grainlines, labels and metadata."""
import json
from html import escape


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
