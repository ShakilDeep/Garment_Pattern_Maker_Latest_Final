"""Cuff size matches source; sleeve placket is anchored at the sleeve placket notch."""
from shapely.geometry import Point, Polygon

from app.domain.drafting import draft
from app.domain.geometry import EPSILON
from app.infrastructure.validation import validate


def test_cuff_matches_source_and_placket_is_placed_on_sleeve_mark(rows):
    measurements = {row["key"]: row["values"]["L"]["value"] for row in rows}
    pieces = {piece["name"]: piece for piece in draft(measurements, "L")["pieces"]}
    cuff, placket, sleeve = pieces["Cuff"], pieces["Sleeve Placket"], pieces["Sleeve"]
    assert cuff["width"] == measurements["cuff_edge_to_edge"]
    assert cuff["height"] == measurements["cuff_width"]
    assert placket["placement"]["on"] == "sleeve"
    anchor = placket["placement"]["anchor"]
    assert anchor == next(mark["point"] for mark in sleeve["marks"] if mark["kind"] == "placket")
    assert Polygon(sleeve["points"]).boundary.distance(Point(anchor)) <= EPSILON
    assert any(
        issue["code"] == "PLACEMENT_CHECK" and issue["severity"] == "PASS"
        for issue in validate({"pieces": list(pieces.values()), "measurements": measurements, "seam_allowance": 0})
    )
