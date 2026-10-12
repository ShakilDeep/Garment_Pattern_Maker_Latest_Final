"""T145 (spec §7 Grading): each chart POM's drafted step between sizes equals the chart step within 0.1 cm."""
from itertools import pairwise

import pytest

from app.application.accuracy.grade_steps import STEP_CM, grade_step_checks
from app.application.cad.style_from_block import style_from_block
from app.domain.blocks.registry import installed
from app.domain.blocks.shirt.measures import DEFINITIONS

POM = "test_body_length"
SIZES = ("S", "M", "L", "XL", "XXL", "3XL")


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


@pytest.fixture(scope="module")
def drafted():
    block = installed().get("shirt_1078375")
    return {size: block.graded_measurements(size)["front_length"] for size in SIZES}


def project(values: dict, source: str = f"chart:{POM}") -> dict:
    """Every size took front_length from chart row 3 (and nothing else from the chart)."""
    sources = {"front_length": source, "bicep": "from_block"}
    patterns = [{"size": size, "input_sources": sources} for size in SIZES]
    return {"measurements": [{"row": 3, "key": POM, "mapping_status": "confirmed",
                              "values": {size: {"value": value} for size, value in values.items()}}],
            "pattern": patterns[2], "grades": patterns[:2] + patterns[3:]}


def test_drafted_steps_equal_to_the_chart_steps_pass(style, drafted):
    checks = grade_step_checks(project(drafted), style, DEFINITIONS)
    assert [c.name for c in checks] == [f"{a}→{b} front_length step (chart {POM})" for a, b in pairwise(SIZES)]
    assert all(c.passed and c.gate and c.source.kind == "chart" for c in checks) and STEP_CM == 0.1
    assert checks[0].piece == "FRT" and checks[0].edge == "FE_hem:HPS" and checks[0].size == "M"


def test_a_chart_step_more_than_a_millimetre_off_fails(style, drafted):
    chart = {**drafted, "XL": drafted["XL"] + 0.15}
    failed = [c.name for c in grade_step_checks(project(chart), style, DEFINITIONS) if not c.passed]
    assert failed == [f"L→XL front_length step (chart {POM})", f"XL→XXL front_length step (chart {POM})"]


def test_inputs_not_from_the_chart_have_no_step_checks(style, drafted):
    assert grade_step_checks(project(drafted, "from_block"), style, DEFINITIONS) == []
