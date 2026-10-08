"""T126 (M1) acceptance: a workbook re-saved without Excel's cached results still parses, and Book2 is stable."""
from io import BytesIO

from openpyxl import load_workbook
from pom_workbooks import BOOK2, CL1086464, chart_values, without_cached_values

from app.infrastructure.chart_parser import parse_chart
from app.infrastructure.parsers import parse_xlsx


def test_the_copy_really_has_no_cached_values():
    copy = load_workbook(BytesIO(without_cached_values(CL1086464.read_bytes())), data_only=True)
    assert copy[" graded spec sheet "]["E15"].value is None


def test_a_copy_without_cached_values_gives_the_same_chart():
    original = parse_chart(CL1086464.read_bytes(), "CL1086464.xlsx")
    copy = parse_chart(without_cached_values(CL1086464.read_bytes()), "CL1086464.xlsx")
    assert (copy.sizes, copy.base_size) == (original.sizes, original.base_size)
    for row in original.measurements:
        assert chart_values(copy, row["key"]) == chart_values(original, row["key"]), row["key"]
    assert copy.measurements[0]["values"]["XS"]["evaluation"] == "formula"


def test_book2_chart_is_s_to_3xl_with_base_l_and_catalog_codes():
    chart = parse_chart(BOOK2.read_bytes(), "Book2(4).xlsx")
    assert chart.sizes == ("S", "M", "L", "XL", "XXL", "3XL")
    assert chart.base_size == "L"
    assert len(chart.measurements) == 35
    assert {row["mapping_status"] for row in chart.measurements} == {"catalog"}
    assert parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx") == chart.measurements
