from itertools import pairwise
from math import isfinite

from shapely.geometry import LineString, Point, Polygon
from shapely.validation import explain_validity

from app.domain.geometry import EPSILON
from app.domain.tolerances import INTERSECTION

REQUIRED_PIECES = {"Front", "Back", "Yoke", "Sleeve", "Collar", "Collar Stand", "Cuff", "Sleeve Placket"}

def structural_checks(pattern):
    results = []
    for p in pattern["pieces"]:
        finite = all(isfinite(value) for point in p["points"] for value in point)
        duplicate_edges = sum(1 for start, end in pairwise(p["points"])
                              if Point(start).distance(Point(end)) <= EPSILON)
        polygon = Polygon(p["points"]) if finite and len(p["points"]) >= 4 else Polygon()
        valid = finite and len(p["points"]) >= 4 and not duplicate_edges and polygon.is_valid and polygon.area > INTERSECTION \
            and Point(p["points"][0]).distance(Point(p["points"][-1])) <= EPSILON
        results.append(
            {
                "code": "GEOMETRY",
                "severity": "PASS" if valid else "ERROR",
                "piece": p["name"],
                "message": f"{p['name']}: closed outline, positive area, no self-intersection"
                if valid
                else f"{p['name']}: invalid outline",
                "rule": "geometry.closed_positive_simple.v1",
                "detail": explain_validity(polygon) if finite else "Non-finite coordinates",
            }
        )
        results.append({"code": "EDGE_QUALITY", "severity": "PASS" if not duplicate_edges else "ERROR",
                        "piece": p["name"], "message": f"{p['name']}: {duplicate_edges} zero-length edges",
                        "actual": duplicate_edges, "expected": 0, "rule": "geometry.edge_length.v1"})
        marks_valid = all(polygon.boundary.distance(Point(mark)) <= EPSILON for mark in p["notches"])
        results.append(
            {
                "code": "NOTCHES",
                "severity": "PASS" if marks_valid else "ERROR",
                "piece": p["name"],
                "message": f"{p['name']}: notch placement {'verified' if marks_valid else 'outside outline'}",
                "rule": "marks.notch_on_outline.v1",
            }
        )
        grain = p.get("grainline", [])
        grain_valid = len(grain) == 2 and all(polygon.covers(Point(mark)) for mark in grain) \
            and LineString(grain).length > EPSILON and polygon.covers(LineString(grain))
        results.append({"code": "GRAINLINE", "severity": "PASS" if grain_valid else "ERROR",
                        "piece": p["name"], "message": f"{p['name']}: grainline "
                        f"{'is contained and oriented' if grain_valid else 'is invalid or outside the piece'}",
                        "rule": "marks.grainline_contained.v1"})
        if pattern.get("seam_allowance", 0) > 0:
            cut = Polygon(p.get("cut_points", []))
            allowance_valid = cut.is_valid and cut.covers(polygon)
            results.append({"code": "SEAM_ALLOWANCE", "severity": "PASS" if allowance_valid else "ERROR",
                            "piece": p["name"], "message": f"{p['name']}: seam allowance offset "
                            f"{'verified' if allowance_valid else 'is invalid'}",
                            "rule": "allowance.offset_contains_seam.v1"})
    return results
