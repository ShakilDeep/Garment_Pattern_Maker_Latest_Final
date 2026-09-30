from copy import deepcopy
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from app.application.service import Service
from app.domain.drafting import draft
from app.infrastructure.geometry_adapter import apply_allowance, marker, validate
from app.infrastructure.parsers import parse_xlsx
from app.infrastructure.repository import Repository

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def values():
    rows = parse_xlsx((ROOT / "references/Book2(4).xlsx").read_bytes(), "source.xlsx")
    return {r["key"]: r["values"]["L"]["value"] for r in rows}


def test_placket_source_choice_changes_geometry(values):
    a = draft(values, "L")
    values["front_placket_width"] += 0.5
    b = draft(values, "L")
    assert a["pieces"][0]["points"] != b["pieces"][0]["points"]


def test_collar_source_dimensions_are_checked(values):
    pattern = draft(values, "L")
    checks = validate(pattern)
    assert any(v["code"] == "COLLAR_SOURCE_CHECK" for v in checks)


def test_generation_clears_outdated_grades(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/db.sqlite"))
    p = service.create("Demo", True)
    p["resolutions"] = {"units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook"}
    service.generate(p, "L")
    service.grade(p, ["L", "M"])
    service.generate(p, "L", 1)
    assert p["grades"] == []


@pytest.mark.parametrize("size", ["S", "M", "L", "XL", "XXL", "3XL"])
def test_all_size_marker_invariants(size):
    rows = parse_xlsx((ROOT / "references/Book2(4).xlsx").read_bytes(), "source.xlsx")
    values = {r["key"]: r["values"][size]["value"] for r in rows}
    p = draft(values, size)
    p["id"] = "test"
    apply_allowance(p, 1)
    result = marker(p, 150, 2, 0.5)
    assert result["valid"]
    shapes = []
    for placed in result["placements"]:
        shape = Polygon([(x + placed["x"], y + placed["y"]) for x, y in placed["points"]])
        assert shape.bounds[0] >= 0 and shape.bounds[1] >= 0
        assert shape.bounds[2] <= result["width"] and shape.bounds[3] <= result["length"]
        for previous in shapes:
            assert shape.distance(previous) >= 0.5 - 1e-6
        shapes.append(shape)
    assert result["utilization"] == pytest.approx(
        100 * sum(p.area for p in shapes) / (result["width"] * result["length"])
    )
    assert marker(p, 150, 2, 0.5) == result


def test_invalid_and_deterministic_geometry(values):
    assert draft(values, "L") == draft(deepcopy(values), "L")
    values["neck_width"] = 1000
    with pytest.raises(ValueError):
        draft(values, "L")


def test_cached_formula_fallback():
    # The supplied fixture has cached values; unsupported formulas must remain reviewable.
    from io import BytesIO

    import openpyxl

    wb = openpyxl.Workbook()
    s = wb.active
    s.append(["Codes", "MEASUREMENTS POINTS", "S", "M"])
    s.append(["10145-A", "Chest", "=SUM(1,2)", 54])
    data = BytesIO()
    wb.save(data)
    row = parse_xlsx(data.getvalue(), "unknown.xlsx")[0]
    assert row["values"]["S"]["value"] is None
    assert row["values"]["S"]["issue"]
