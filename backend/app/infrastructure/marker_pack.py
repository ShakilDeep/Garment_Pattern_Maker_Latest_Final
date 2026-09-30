"""Pure first-fit packer for marker instances."""
from shapely.geometry import Polygon, box

from app.domain.geometry import EPSILON


def pack_instances(instances: list[dict], width: float, gap: float) -> dict:
    rows: list[dict[str, float]] = []
    placements = []
    for p in instances:
        if p["width"] + 2 * gap > width:
            raise ValueError(f"Fabric width must exceed {p['width'] + 2 * gap:.1f} cm for {p['name']}")
        row = next((r for r in rows if r["x"] + p["width"] + gap <= width and p["height"] <= r["height"]), None)
        if row is None:
            row = {"x": gap, "y": gap + sum(r["height"] + gap for r in rows), "height": p["height"]}
            rows.append(row)
        placements.append({**p, "x": row["x"], "y": row["y"]})
        row["x"] += p["width"] + gap
    used_length = sum(r["height"] + gap for r in rows) + gap
    utilization = sum(p["area"] for p in placements) / (width * used_length) * 100
    shapes = [Polygon([(x + p["x"], y + p["y"]) for x, y in p["points"]]) for p in placements]
    fabric = box(0, 0, width, used_length)
    valid = all(s.is_valid and fabric.covers(s) for s in shapes)
    for i, shape in enumerate(shapes):
        for other in shapes[:i]:
            if shape.distance(other) < gap - EPSILON:
                valid = False
    if not valid:
        raise ValueError("Marker failed independent bounds or spacing validation")
    return {
        "placements": placements, "width": width, "length": used_length, "gap": gap,
        "utilization": utilization, "waste": 100 - utilization, "valid": valid,
    }
