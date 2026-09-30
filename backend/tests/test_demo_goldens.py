"""Demo regression evidence, never a claim of client production calibration."""

import json
from hashlib import sha256
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

from app.application.requirements import requirements
from app.domain.back_yoke import back_shoulder_half
from app.domain.catalog import SIZES
from app.domain.drafting import draft
from app.infrastructure.marker import marker_batch
from app.infrastructure.parsers import parse_pdf
from app.infrastructure.validation import validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def golden():
    return json.loads((ROOT / "fixtures/demo_v1_metrics.json").read_text())


def values_for(rows, size):
    return {row["key"]: row["values"][size]["value"] for row in rows}


def test_golden_source_and_profile_are_explicit(golden):
    assert golden["source_sha256"] == sha256((ROOT / "references/Book2(4).xlsx").read_bytes()).hexdigest()
    assert golden["profile"] == "demo_v1"
    assert golden["profile_version"] == "1.0.0"
    assert golden["production_certified"] is False
    assert set(golden["sizes"]) == set(SIZES)


def test_parser_and_requirement_goldens(golden, rows):
    assert rows == golden["parsed_measurements"]
    data = (ROOT / "references/1078983(5).pdf").read_bytes()
    assert sha256(data).hexdigest() == golden["techpack_sha256"]
    tech = parse_pdf(data, "1078983(5).pdf")
    assert {key: tech[key] for key in golden["techpack_metadata"]} == golden["techpack_metadata"]
    project = {"id": "golden", "measurements": rows, "techpack": tech, "documents": [], "resolutions": {}}
    for size in SIZES:
        for state, resolutions in [("unreviewed", {}), ("demo_ready", golden["demo_resolutions"])]:
            project["resolutions"] = resolutions
            result = requirements(project, size)
            actual = {
                "ready": result["ready"],
                "items": [{key: r[key] for key in ("key", "status", "blocking")} for r in result["items"]],
            }
            assert actual == golden["sizes"][size]["requirements"][state]


@pytest.mark.parametrize("size", SIZES)
def test_all_piece_metrics_and_source_values_match_golden(rows, golden, size):
    values = values_for(rows, size)
    expected = golden["sizes"][size]
    assert values == expected["measurements"]
    pattern = draft(values, size)
    assert pattern == draft(values, size)
    assert len(pattern["pieces"]) == len(expected["pieces"]) == 8
    assert pattern["profile_metadata"]["version"] == golden["profile_version"]
    for piece in pattern["pieces"]:
        metrics = expected["pieces"][piece["id"]]
        for key in ("width", "height", "area", "perimeter"):
            assert piece[key] == pytest.approx(metrics[key], abs=1e-6, rel=0), (size, piece["id"], key)
        assert piece["seams"] == pytest.approx(metrics["seams"], abs=1e-6, rel=0)
        assert piece["quantity"] == metrics["quantity"]
        shape = Polygon(piece["points"])
        assert shape.is_valid and shape.area > 0
        assert shape.area == pytest.approx(piece["area"], abs=1e-6, rel=0)
        assert shape.length == pytest.approx(piece["perimeter"], abs=1e-6, rel=0)
        assert piece["points"][0] == piece["points"][-1]
    assert not [i for i in validate(pattern) if i["severity"] == "ERROR"]


@pytest.mark.parametrize("size", SIZES)
def test_component_dimensions_are_compared_to_component_source_targets(rows, size):
    pattern = draft(values_for(rows, size), size)
    dimensions = [i for i in validate(pattern) if i["code"] == "DIMENSION_CHECK"]
    assert dimensions
    assert all(i["severity"] == "PASS" for i in dimensions), dimensions
    by_name = {p["name"]: p for p in pattern["pieces"]}
    m = pattern["measurements"]
    assert by_name["Sleeve"]["height"] == pytest.approx(m["sleeve_length"] - m["cuff_width"])
    assert by_name["Cuff"]["height"] == pytest.approx(m["cuff_width"])
    assert by_name["Cuff"]["width"] == pytest.approx(m["cuff_edge_to_edge"])
    assert by_name["Sleeve Placket"]["height"] == pytest.approx(m["sleeve_placket_length"])
    assert by_name["Sleeve Placket"]["width"] == pytest.approx(m["sleeve_placket_width"])
    assert by_name["Yoke"]["width"] == pytest.approx(
        2 * back_shoulder_half(m["shoulder_point_to_point"] / 2, m)
    )
    codes = {issue["code"] for issue in validate(pattern)}
    assert {"GEOMETRY", "SEAM_CHECK", "DIMENSION_CHECK", "NOTCHES", "GRAINLINE", "PLACEMENT_CHECK"} <= codes


def test_fixed_mixed_marker_metrics_and_independent_spacing(rows, golden):
    config = golden["marker"]["config"]
    patterns = {s: {**draft(values_for(rows, s), s), "id": f"golden:{s}"} for s in config["quantities"]}
    result = marker_batch(patterns, **config)
    assert result == marker_batch(patterns, **config)
    for key in ("length", "utilization", "waste"):
        assert result[key] == pytest.approx(golden["marker"][key], abs=1e-6, rel=0)
    assert len(result["placements"]) == golden["marker"]["placements"]
    shapes = []
    for p in result["placements"]:
        shape = Polygon([(x + p["x"], y + p["y"]) for x, y in p["points"]])
        assert box(0, 0, result["width"], result["length"]).covers(shape)
        assert all(shape.distance(other) >= config["gap"] - 1e-6 for other in shapes)
        shapes.append(shape)
