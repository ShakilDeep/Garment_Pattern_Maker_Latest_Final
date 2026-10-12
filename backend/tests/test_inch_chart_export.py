"""T146 (spec §7 Export): an inch chart drafts and exports cm geometry, and its tolerances are checked in cm."""
import io
import zipfile

import pytest
from named_project import shirt_project
from test_accuracy_chart_checks import project as chart_project
from test_chart_driven_project import POM, ROW, chart_values

from app.application import block_inputs
from app.application.accuracy.chart_checks import chart_checks
from app.application.cad.style_from_block import style_from_block
from app.application.grading.project_aama import project_graded_aama
from app.application.requirement_resolve import resolve
from app.domain.blocks.chart_map import ChartMapEntry
from app.domain.blocks.registry import installed
from app.domain.blocks.shirt.measures import DEFINITIONS
from app.domain.units import CM_PER_INCH
from app.infrastructure.aama.reader import read_aama

SAME_CM = 0.05  # spec §7: re-read geometry within 0.05 cm


def test_an_inch_chart_tolerance_is_checked_in_cm():
    drafted = installed().get("shirt_1078375").graded_measurements("L")["front_length"]
    project = chart_project(drafted + 0.4, 0.2)  # chart value already in cm; its tolerance column in inches
    project["measurements"][0]["source_unit"] = "inch"
    (check,) = chart_checks(project, style_from_block("shirt_1078375"), DEFINITIONS)
    assert check.limit == f"{drafted + 0.4:.3f} ± 0.508 cm" and check.passed


def _exported(path, chart: dict[str, float], unit: str) -> tuple[str, dict]:
    def add_row(project: dict) -> None:
        project["measurements"].append({"row": ROW, "key": POM, "code": POM, "label": "half chest", "unit": unit,
                                        "tolerance": 0.2, "mapping_status": "confirmed",
                                        "values": {size: {"value": v} for size, v in chart.items()}})
        project["chart"]["rows"].append({"ref": str(ROW), "tolerance": 0.2})
        resolve(project, "units", unit)

    _, project = shirt_project(path, prepare=add_row)
    archive = zipfile.ZipFile(io.BytesIO(project_graded_aama(project, "mm")[0]))
    return archive.read("base.dxf").decode(), {p.name: p.cut for p in read_aama(archive.read("base.dxf")).pieces}


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    entry = ChartMapEntry("half_chest_front", POM, "confirmed", "test: pattern maker confirmed")
    centimetres = chart_values("half_chest_front")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(block_inputs, "chart_map", lambda block: (entry,))
        inches = {size: value / CM_PER_INCH for size, value in centimetres.items()}
        return (_exported(tmp_path_factory.mktemp("cm"), centimetres, "cm"),
                _exported(tmp_path_factory.mktemp("inch"), inches, "inch"))


def test_an_inch_chart_exports_the_same_cm_geometry_in_a_metric_file(exports):
    (cm_text, cm_cuts), (inch_text, inch_cuts) = exports
    assert "UNITS: METRIC" in inch_text and "UNITS: METRIC" in cm_text
    assert cm_cuts.keys() == inch_cuts.keys()
    for name, cut in inch_cuts.items():
        assert len(cut) == len(cm_cuts[name]), name
        gap = max(max(abs(a - c), abs(b - d)) for (a, b), (c, d) in zip(cut, cm_cuts[name], strict=True))
        assert gap <= SAME_CM, name
