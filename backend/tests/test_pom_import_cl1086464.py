"""T126 (M1) acceptance: the CL1086464 pant workbook imports as a generic measurement chart."""
import pytest
from pom_workbooks import CL1086464, chart_row, chart_values

from app.infrastructure.chart_parser import parse_chart

PANT_KEYS = {
    "half_waist", "waist_extended", "hip_position_side", "hip_position_cf", "half_seat", "thigh_width",
    "front_rise", "back_rise", "knee_width", "half_leg_opening", "hem_height", "inseam",
    "waistband_width", "front_pocket_opening_waist", "front_pocket_opening_side", "pocket_bag_depth",
    "half_drawcord_length",
}


@pytest.fixture(scope="module")
def chart():
    return parse_chart(CL1086464.read_bytes(), "CL1086464.xlsx")


def test_table_sizes_and_base_size(chart):
    assert (chart.sheet, chart.header_row) == (" graded spec sheet ", 14)
    assert chart.sizes == ("XS", "S", "M", "L", "XL", "XXL")
    assert chart.base_size == "S"
    assert chart.unit_hint is None


def test_build_plan_values(chart):
    assert chart_values(chart, "half_waist") == [33, 35, 37, 39.5, 42, 44.5]
    assert chart_values(chart, "inseam") == [77, 78, 79, 80, 81, 82]
    assert chart_values(chart, "half_seat") == [50, 52, 54, 56.5, 59, 61.5]
    assert chart_values(chart, "front_pocket_opening_waist") == [3, 3, 3.5, 3.5, 4, 4.5]


def test_every_pom_is_mapped_through_the_synonym_table(chart):
    assert len(chart.measurements) == 17
    assert {row["key"] for row in chart.measurements} == PANT_KEYS
    assert {row["mapping_status"] for row in chart.measurements} == {"synonym"}
    assert next(row for row in chart.measurements if row["key"] == "half_seat")["mapped_from"] == "1/2 SEAT"


def test_half_flags_tolerances_and_alternative_names(chart):
    halves = {key for key in PANT_KEYS if chart_row(chart, key).half}
    assert halves == {"half_waist", "half_seat", "half_leg_opening", "half_drawcord_length"}
    assert chart_row(chart, "inseam").tolerance == 0.5
    assert chart_row(chart, "half_waist").tolerance == 1.0
    assert chart_row(chart, "half_waist").alt_label == "BEL  (DURGUN)"


def test_header_meta_and_the_declared_size_range_conflict(chart):
    assert chart.meta["style"] == "1086464"
    assert chart.meta["description"] == "pant"
    assert chart.meta["fit"] == "high rise / wide leg"
    assert chart.issues == ("The header declares size range XS–XL but the table has XS–XXL",)


def test_legacy_rows_keep_their_shape(chart):
    row = chart.measurements[0]
    assert list(row) == [
        "key", "mapping_status", "mapped_from", "code", "label", "original_label", "parser_version",
        "unit", "confidence", "tolerance", "source", "sheet", "row", "values",
    ]
    assert (row["code"], row["unit"], row["tolerance"]) == ("20125", "unconfirmed", "1")
    assert row["values"]["XS"]["formula"] == "=F15-2"
