"""Back/yoke demo_v1 must consume source forward-shoulder values."""
import pytest

from app.domain.drafting import draft


def _piece(pattern, name):
    return next(item for item in pattern["pieces"] if item["name"] == name)


def test_forward_shoulder_armhole_shortens_back_and_yoke(rows):
    measurements = {row["key"]: row["values"]["L"]["value"] for row in rows}
    base = draft(measurements, "L")
    shifted = draft(
        {**measurements, "forward_shoulder_armhole": measurements["forward_shoulder_armhole"] + 1},
        "L",
    )
    assert _piece(shifted, "Yoke")["width"] < _piece(base, "Yoke")["width"]
    assert _piece(shifted, "Back")["seams"]["yoke"] < _piece(base, "Back")["seams"]["yoke"]
    assert _piece(shifted, "Yoke")["seams"]["yoke"] == pytest.approx(_piece(shifted, "Back")["seams"]["yoke"])
