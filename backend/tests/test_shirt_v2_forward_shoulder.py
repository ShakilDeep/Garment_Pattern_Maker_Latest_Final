"""T147: shirt_v2's front neck sits inside the yoke neck by the 1078375 PDS amount (FRT 8.62 vs YK 9.18 cm);
the shoulder seams that this leaves unequal are reported, not gated (Q13). The waist level comes from the chart
or is asked for; it is never placed by a default share of the body length."""
import pytest
from pom_workbooks import BOOK2

from app.application.measurement_requirements import measurement_items
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.catalog import SIZES
from app.domain.profiles import SHIRT_V2
from app.domain.shirt_v2.body import front_half, yoke_half
from app.domain.shirt_v2.draft import draft_v2
from app.infrastructure.parsers import parse_xlsx
from app.infrastructure.seam_checks import seam_checks

R = reference_measurements()
INSET = R["back_neck_width"] - R["front_neck_width"]  # 0.56 cm on the PDS sew line
ROWS = parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx")


def chart(size: str) -> dict:
    return {row["key"]: row["values"][size]["value"] for row in ROWS
            if row["values"].get(size, {}).get("value") is not None and row["mapping_status"] != "unmapped"}


@pytest.mark.parametrize("size", SIZES)
def test_the_front_neck_is_the_pds_inset_inside_the_yoke_neck(size):
    m = chart(size)
    front, yoke = front_half(m)["neckline"][-1], yoke_half(m, 2.0)["neckline"][-1]
    assert yoke[0] - front[0] == pytest.approx(INSET, abs=1e-9)
    assert INSET == pytest.approx(0.56, abs=1e-9)


def test_the_unequal_shoulder_seams_are_reported_as_a_warning():
    rows = {row.get("name"): row for row in seam_checks(draft_v2(chart("L"), "L", SHIRT_V2))}
    shoulder = rows["Shoulder seam"]
    assert shoulder["severity"] == "WARNING"
    assert (shoulder["actual"], shoulder["expected"]) == (pytest.approx(17.78, abs=0.01),
                                                          pytest.approx(16.76, abs=0.01))


def test_a_neck_narrower_than_the_inset_is_refused():
    with pytest.raises(ValueError, match="incompatible"):
        draft_v2({**chart("L"), "neck_width": 2 * INSET}, "L", SHIRT_V2)


def test_a_chart_without_a_waist_position_is_not_drafted():
    m = chart("L")
    del m["waist_position_hps"]
    with pytest.raises(ValueError, match="Missing positive measurements: waist_position_hps"):
        draft_v2(m, "L", SHIRT_V2)


@pytest.mark.parametrize(("profile", "asked"), [("shirt_v2", True), ("demo_v1", False)])
def test_a_missing_waist_position_is_asked_for_by_shirt_v2_only(profile, asked):
    rows = [row for row in ROWS if row["key"] != "waist_position_hps"]
    items: list[str] = []
    measurement_items({"resolutions": {"profile": profile}, "measurements": rows}, "L",
                      lambda key, *_args, **_kw: items.append(key))
    assert ("measurement:waist_position_hps" in items) is asked
