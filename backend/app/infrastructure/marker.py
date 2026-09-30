from shapely.geometry import Polygon

from app.infrastructure.marker_search import search_marker


def _instances(pattern, quantity):
    instances = []
    for p in pattern["pieces"]:
        polygon = Polygon(p.get("cut_points", p["points"]))
        x0, y0, x1, y1 = polygon.bounds
        points = [[x - x0, y - y0] for x, y in polygon.exterior.coords]
        for i in range(p["quantity"] * quantity):
            instances.append({
                "name": p["name"], "size": pattern["size"], "pattern_id": pattern["id"],
                "piece_id": p["id"], "instance": i, "points": points,
                "width": x1 - x0, "height": y1 - y0, "area": polygon.area, "rotation": 0,
            })
    return instances


def marker_batch(patterns, width, quantities, gap, seed=0, time_budget_ms=250, iterations=1, grain_policy="vertical"):
    if not quantities or sum(quantities.values()) > 20:
        raise ValueError("Choose between 1 and 20 garments per marker")
    if any(type(q) is not int or q < 1 for q in quantities.values()):
        raise ValueError("Garment quantities must be positive whole numbers")
    ordered_sizes = sorted(quantities)
    instances = [p for size in ordered_sizes for p in _instances(patterns[size], quantities[size])]
    instances.sort(key=lambda p: (-p["height"], -p["width"], p["name"], p["size"], p["instance"]))
    return search_marker(
        instances, width, gap, quantities, ordered_sizes, patterns,
        seed, time_budget_ms, iterations, grain_policy,
    )
