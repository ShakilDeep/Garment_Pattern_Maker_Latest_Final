"""T145: a 1078375 size graded from chart values: followers follow, pair partners balance, seams re-trued,
and a chart value is never moved (owner decisions 2026-10-12)."""
import pytest

from app.domain.blocks.shirt.chart_grade import FROM_BLOCK, grade_from_chart
from app.domain.blocks.shirt.reference import graded_measurements, reference_measurements
from app.domain.blocks.shirt.truing import relation_values

HELD_CM = 1e-5


@pytest.fixture(scope="module")
def targets():
    return relation_values(reference_measurements())


def off_target(values, targets) -> set[str]:
    reached = relation_values(values)
    return {name for name, value in reached.items() if abs(value - targets[name]) > HELD_CM}


def test_without_chart_values_the_size_is_the_pds_grading():
    graded = grade_from_chart("XL", {})
    assert graded.values == graded_measurements("XL") and graded.unheld == ()
    assert set(graded.sources.values()) == {FROM_BLOCK}


def test_a_chart_chest_is_kept_its_hem_follows_and_the_seams_are_trued(targets):
    pds = graded_measurements("XL")
    graded = grade_from_chart("XL", {"half_chest_front": pds["half_chest_front"] + 1.0})
    assert graded.values["half_chest_front"] == pds["half_chest_front"] + 1.0
    assert graded.values["front_hem_width"] == pytest.approx(pds["front_hem_width"] + 1.0)
    assert graded.sources["half_chest_front"] == "chart"
    assert graded.sources["front_hem_width"] == "follows:half_chest_front"
    assert graded.unheld == () and not off_target(graded.values, targets)
    assert any(source.startswith("trued:") for source in graded.sources.values())


def test_a_chart_yoke_depth_is_balanced_by_its_partner():
    pds = graded_measurements("M")
    graded = grade_from_chart("M", {"yoke_depth_cb": pds["yoke_depth_cb"] + 0.5})
    assert graded.values["back_neck_rise"] == pytest.approx(pds["back_neck_rise"] - 0.5)
    assert graded.sources["back_neck_rise"] == "balances:yoke_depth_cb"


def test_a_chart_value_a_seam_is_solved_with_wins_and_the_seam_is_left_unheld(targets):
    pds = graded_measurements("XL")
    chart = {"back_armhole_depth": pds["back_armhole_depth"] + 1.0}
    graded = grade_from_chart("XL", chart)
    assert graded.values["back_armhole_depth"] == chart["back_armhole_depth"]
    assert graded.unheld == ("side seams",)
    assert off_target(graded.values, targets) == {"side seams"}


def test_a_locked_partner_is_never_moved():
    pds = graded_measurements("S")
    chart = {"cap_height": pds["cap_height"] + 0.3, "underarm_height": pds["underarm_height"]}
    graded = grade_from_chart("S", chart)
    assert {name: graded.values[name] for name in chart} == chart
    assert graded.unheld == ("sleeve cap ease",)
