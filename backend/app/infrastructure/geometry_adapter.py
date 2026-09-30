from shapely.geometry import Polygon

from app.infrastructure.validation import validate

__all__ = ["apply_allowance", "marker", "validate"]

def apply_allowance(pattern, allowance):
    for p in pattern["pieces"]:
        polygon = Polygon(p["points"]).buffer(allowance, join_style="mitre")
        if polygon.geom_type != "Polygon" or not polygon.is_valid:
            raise ValueError("Seam allowance produced invalid cut geometry")
        p["cut_points"] = [[round(x, 6), round(y, 6)] for x, y in polygon.exterior.coords]
    pattern["seam_allowance"] = allowance


def marker(pattern, width, quantity, gap):
    from app.infrastructure.marker import marker_batch

    return marker_batch({pattern['size']: pattern}, width, {pattern['size']: quantity}, gap)
