"""T142: each block input comes from a confirmed chart mapping, else the accepted reference, else is missing."""
import pytest

from app.application import block_inputs as module
from app.application.block_inputs import FROM_BLOCK, block_inputs
from app.domain.blocks.chart_map import ChartMapEntry
from app.domain.blocks.registry import installed

BLOCK = installed().get("shirt_1078375")
CHART_FRONT = 80.5


def _project(accepted=False):
    row = {"key": "front_length_hps", "mapping_status": "auto", "values": {"L": {"value": CHART_FRONT}}}
    return {"measurements": [row], "resolutions": {"block_reference": "accepted"} if accepted else {}}


def _mapped(monkeypatch, status):
    entry = ChartMapEntry("front_length", "front_length_hps", status, "pattern maker note")
    monkeypatch.setattr(module, "chart_map", lambda block: (entry,))


def test_a_confirmed_mapping_reads_the_chart(monkeypatch):
    _mapped(monkeypatch, "confirmed")
    inputs = block_inputs(_project(accepted=True), BLOCK, "L")
    assert inputs.values["front_length"] == CHART_FRONT and inputs.sources["front_length"] == "chart:front_length_hps"
    assert inputs.missing == ()


def test_a_proposed_mapping_is_never_used(monkeypatch):
    _mapped(monkeypatch, "proposed")
    inputs = block_inputs(_project(accepted=True), BLOCK, "L")
    assert inputs.sources["front_length"] == FROM_BLOCK
    assert inputs.values["front_length"] == BLOCK.graded_measurements("L")["front_length"]


def test_the_accepted_reference_fills_every_unmapped_input():
    inputs = block_inputs(_project(accepted=True), BLOCK, "M")
    assert inputs.values == dict(BLOCK.graded_measurements("M"))
    assert set(inputs.sources.values()) == {FROM_BLOCK} and len(inputs.sources) == len(BLOCK.required)


def test_without_acceptance_every_unmapped_input_is_missing():
    inputs = block_inputs(_project(), BLOCK, "L")
    assert inputs.values == {} and inputs.missing == BLOCK.required


def test_a_size_outside_the_reference_is_missing_even_when_accepted():
    assert "XS" not in BLOCK.graded_sizes()
    assert block_inputs(_project(accepted=True), BLOCK, "XS").missing == BLOCK.required


@pytest.mark.parametrize("status", ["unmapped", "not_used"])
def test_a_confirmed_mapping_skips_an_unmapped_chart_row(monkeypatch, status):
    _mapped(monkeypatch, "confirmed")
    project = _project()
    project["measurements"][0]["mapping_status"] = status
    assert "front_length" in block_inputs(project, BLOCK, "L").missing
