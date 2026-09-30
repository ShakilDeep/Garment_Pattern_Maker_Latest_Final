"""Sleeve construction marks must come from source placket/pleat values."""
from shapely.geometry import Point, Polygon

from app.domain.drafting import draft
from app.domain.geometry import EPSILON


def test_sleeve_placket_and_pleat_marks_use_source_and_sit_on_outline(rows):
    measurements = {row["key"]: row["values"]["L"]["value"] for row in rows}
    sleeve = next(piece for piece in draft(measurements, "L")["pieces"] if piece["name"] == "Sleeve")
    kinds = {mark["kind"] for mark in sleeve["marks"]}
    assert kinds >= {"placket", "pleat"}
    outline = Polygon(sleeve["points"]).boundary
    for mark in sleeve["marks"]:
        assert outline.distance(Point(mark["point"])) <= EPSILON
        assert mark["point"] in sleeve["notches"]
    longer = draft({**measurements, "sleeve_placket_length": measurements["sleeve_placket_length"] + 1}, "L")
    base_placket = next(mark for mark in sleeve["marks"] if mark["kind"] == "placket")["point"]
    moved = next(
        mark for mark in next(p for p in longer["pieces"] if p["name"] == "Sleeve")["marks"]
        if mark["kind"] == "placket"
    )["point"]
    assert moved != base_placket
