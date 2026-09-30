"""Specification: construction placements must land on the host piece outline."""
from shapely.geometry import Point, Polygon

from app.domain.geometry import EPSILON


def placement_checks(pattern):
    pieces = {piece["name"]: piece for piece in pattern.get("pieces", [])}
    placket, sleeve = pieces.get("Sleeve Placket"), pieces.get("Sleeve")
    if not placket or not sleeve:
        return []
    placement = placket.get("placement") or {}
    anchor = placement.get("anchor")
    on_sleeve = placement.get("on") == "sleeve" and anchor is not None
    on_outline = on_sleeve and Polygon(sleeve["points"]).boundary.distance(Point(anchor)) <= EPSILON
    return [{
        "code": "PLACEMENT_CHECK",
        "severity": "PASS" if on_outline else "ERROR",
        "piece": "Sleeve Placket",
        "message": "Sleeve placket anchor is on the sleeve outline"
        if on_outline else "Sleeve placket is missing a sleeve-outline anchor",
        "rule": "construction.placement_on_host.v1",
    }]
