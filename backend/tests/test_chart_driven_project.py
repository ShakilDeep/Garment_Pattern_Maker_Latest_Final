"""T145: a 1078375 project whose chest comes from a confirmed chart entry is graded from the chart.

No entry is confirmed for the client yet (Q6), so the test confirms one and adds the chart row itself.
"""
import pytest
from named_project import GRADED, shirt_project

from app.application import block_inputs
from app.application.accuracy.project_report import accuracy_report
from app.application.grading.grade_rules import grade_rules
from app.application.project_style import project_style
from app.domain.blocks.chart_map import ChartMapEntry
from app.domain.blocks.registry import installed
from app.domain.pattern.ids import PieceId, PointId
from app.infrastructure.aama.rul import read_rul, write_rul

POM, ROW, STEP_CM = "test_half_chest", 990, 0.5
SIZES = ("S", "M", "L", "XL", "XXL", "3XL")


def chart_values(name: str) -> dict[str, float]:
    """The PDS grading's value plus 0.5 cm per size from L: a chart that grades faster than the PDS."""
    block = installed().get("shirt_1078375")
    return {size: block.graded_measurements(size)[name] + STEP_CM * (i - SIZES.index("L"))
            for i, size in enumerate(SIZES)}


def charted(path, monkeypatch, name: str):
    entry = ChartMapEntry(name, POM, "confirmed", "test: pattern maker confirmed")
    monkeypatch.setattr(block_inputs, "chart_map", lambda block: (entry,))
    values = chart_values(name)

    def add_row(project: dict) -> None:
        project["measurements"].append({"row": ROW, "key": POM, "code": POM, "label": name, "unit": "cm",
                                        "tolerance": 0.5, "mapping_status": "confirmed",
                                        "values": {size: {"value": v} for size, v in values.items()}})
        project["chart"]["rows"].append({"ref": str(ROW), "tolerance": 0.5})

    return shirt_project(path, prepare=add_row)[1], values


@pytest.fixture(scope="module")
def chest(tmp_path_factory):
    with pytest.MonkeyPatch.context() as monkeypatch:
        return charted(tmp_path_factory.mktemp("chest"), monkeypatch, "half_chest_front")


def test_the_chart_drives_the_chest_and_its_followers(chest):
    project, _ = chest
    sources = {grade["size"]: grade["input_sources"] for grade in project["grades"]} | {
        "L": project["pattern"]["input_sources"]}
    assert set(sources) == {"L", *GRADED}
    for size_sources in sources.values():
        assert size_sources["half_chest_front"] == f"chart:{POM}"
        assert size_sources["front_hem_width"] == "follows:half_chest_front"


def test_the_report_is_ready_and_every_chart_step_is_checked(chest):
    project, _ = chest
    report = accuracy_report(project)
    failed = [c["name"] for c in report["checks"] if c["gate"] and not c["passed"]]
    assert not failed, failed
    steps = [c for c in report["checks"] if c["name"].endswith(f"step (chart {POM})")]
    assert len(steps) == len(SIZES) - 1 and all(c["source"]["kind"] == "chart" for c in steps)


def test_the_rul_carries_the_chart_step(chest):
    project, values = chest
    rules = grade_rules(project_style(project))
    table = read_rul(write_rul(rules.table, "mm"))
    front = PieceId("FRT")
    ua, neck = (table.rules[rules.by_point[(front, PointId(n))] - 1] for n in ("UA", "CF_neck"))
    for index, size in enumerate(table.sizes):
        assert ua[index][1] - neck[index][1] == pytest.approx(values[size] - values["L"], abs=0.01), size


def test_a_chart_value_a_seam_is_solved_with_blocks_export(tmp_path, monkeypatch):
    project, _ = charted(tmp_path, monkeypatch, "back_armhole_depth")
    report = accuracy_report(project)
    failed = {c["name"] for c in report["checks"] if c["gate"] and not c["passed"]}
    assert report["status"] == "errors" and "XL side seams" in failed
