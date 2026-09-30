"""Collar piece records source calibration targets without changing demo geometry."""
from app.domain.drafting import draft


def test_collar_records_source_calibration_targets(rows):
    measurements = {row["key"]: row["values"]["L"]["value"] for row in rows}
    collar = next(piece for piece in draft(measurements, "L")["pieces"] if piece["name"] == "Collar")
    targets = collar["source_targets"]
    assert targets["attachment"] == collar["seams"]["attachment"]
    assert targets["buttoned_length"] == measurements["collar_buttoned_length"]
    assert targets["outside_edge"] == measurements["collar_outside_edge"]
