"""T143 (spec §0.1): every chart-sourced input, measured on the drafted sew line, is within the chart's tolerance."""
import pytest

from app.application.accuracy.chart_checks import chart_checks
from app.application.cad.style_from_block import style_from_block
from app.domain.blocks.registry import installed
from app.domain.blocks.shirt.measures import DEFINITIONS

POM = "body_length_hps"


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


@pytest.fixture(scope="module")
def drafted_l():
    return installed().get("shirt_1078375").graded_measurements("L")["front_length"]


def project(value: float, tolerance: float | None) -> dict:
    """A project whose L front length came from chart row 7 (as a confirmed chart-map entry records it)."""
    return {
        "measurements": [{"row": 7, "key": POM, "mapping_status": "confirmed", "values": {"L": {"value": value}}}],
        "chart": {"rows": [{"ref": "7", "tolerance": tolerance}]},
        "pattern": {"size": "L", "input_sources": {"front_length": f"chart:{POM}", "placket_rise": "from_block"}},
        "grades": [],
    }


def test_a_chart_value_the_draft_honours_passes(style, drafted_l):
    (check,) = chart_checks(project(drafted_l + 0.4, 0.5), style, DEFINITIONS)
    assert check.passed and check.gate
    assert (check.size, check.piece, check.edge) == ("L", "FRT", "FE_hem:HPS")
    assert check.value == pytest.approx(drafted_l)
    assert check.source.kind == "chart" and POM in check.source.ref
    assert check.limit == f"{drafted_l + 0.4:.3f} ± 0.5 cm"


def test_a_draft_outside_the_chart_tolerance_fails(style, drafted_l):
    (check,) = chart_checks(project(drafted_l + 0.6, 0.5), style, DEFINITIONS)
    assert not check.passed and check.gate


def test_a_zero_tolerance_needs_the_exact_value(style, drafted_l):
    assert chart_checks(project(drafted_l, 0.0), style, DEFINITIONS)[0].passed
    assert not chart_checks(project(drafted_l + 0.01, 0.0), style, DEFINITIONS)[0].passed


def test_a_row_without_a_tolerance_fails_and_is_never_guessed(style, drafted_l):
    (check,) = chart_checks(project(drafted_l, None), style, DEFINITIONS)
    assert not check.passed and check.gate
    assert check.limit == "chart gives no tolerance"


def test_inputs_from_the_block_are_not_chart_checks(style):
    sources = {"pattern": {"size": "L", "input_sources": {"front_length": "from_block"}}, "grades": []}
    assert chart_checks({**project(0, 0.5), **sources}, style, DEFINITIONS) == []
