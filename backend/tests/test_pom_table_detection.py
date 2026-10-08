"""T126 (M1) / P1-18: the POM table is found on any sheet, with any size labels, and never guessed."""
import pytest
from pom_workbooks import chart_values, workbook_bytes

from app.infrastructure.chart_parser import parse_chart

HEADER = ["Codes", "MEASUREMENTS POINTS", 4, "4½", 5, "TOLERANCE"]
ROWS = [["A1", "1/2 WAIST", 30, 31, 32, 1], ["A2", "INSEAM", 70, "=C3+1", "=D3+1", "0,5"]]


def test_half_sizes_and_numeric_labels_become_the_size_list():
    chart = parse_chart(workbook_bytes(("Chart", [HEADER, *ROWS])), "kids.xlsx")
    assert chart.sizes == ("4", "4½", "5")
    assert chart_values(chart, "inseam") == [70, 71, 72]
    assert chart.base_size == "4"


def test_the_table_is_found_after_a_cover_sheet():
    cover = ("Cover", [["STYLE#", None, "X1"], ["Comments", "none"]])
    chart = parse_chart(workbook_bytes(cover, ("Spec", [["title"], HEADER, *ROWS])), "spec.xlsx")
    assert (chart.sheet, chart.header_row) == ("Spec", 2)


def test_the_sheet_with_the_most_size_columns_wins():
    single = ("Base only", [["POM", "MEASUREMENTS POINTS", "S"], ["A1", "1/2 WAIST", 35]])
    chart = parse_chart(workbook_bytes(single, ("Graded", [HEADER, *ROWS])), "two.xlsx")
    assert chart.sheet == "Graded"


def test_an_unlabelled_text_column_is_kept_as_the_alternative_name_not_a_size():
    rows = [["POM", "MEASUREMENTS POINTS", None, "S", "M"], ["A1", "1/2 WAIST", "BEL", 35, 37]]
    chart = parse_chart(workbook_bytes(("Chart", rows)), "alt.xlsx")
    assert chart.sizes == ("S", "M")
    assert chart.rows[0].alt_label == "BEL"


def test_an_all_typed_chart_has_no_detectable_base_size():
    rows = [["Codes", "MEASUREMENTS POINTS", "S", "M"], ["A1", "1/2 WAIST", 35, 37]]
    assert parse_chart(workbook_bytes(("Chart", rows)), "typed.xlsx").base_size is None


def test_duplicate_size_labels_are_rejected():
    rows = [["Codes", "MEASUREMENTS POINTS", "S", "S"], ["A1", "1/2 WAIST", 35, 37]]
    with pytest.raises(ValueError, match="Duplicate size label S"):
        parse_chart(workbook_bytes(("Chart", rows)), "dup.xlsx")


def test_a_workbook_without_a_table_is_rejected():
    with pytest.raises(ValueError, match="No measurement rows with size headers found"):
        parse_chart(workbook_bytes(("Notes", [["hello", "world"]])), "notes.xlsx")


def test_an_unsupported_formula_without_a_cache_is_not_guessed():
    rows = [["Codes", "MEASUREMENTS POINTS", "S", "M"], ["A1", "1/2 WAIST", 35, "=SUM(1,2)"]]
    cell = parse_chart(workbook_bytes(("Chart", rows)), "f.xlsx").measurements[0]["values"]["M"]
    assert (cell["value"], cell["issue"]) == (None, "Unresolved numeric value or unsupported formula")


def test_unknown_names_stay_unmapped_with_their_code_as_key():
    rows = [["Codes", "MEASUREMENTS POINTS", "S", "M"], ["Z9", "MYSTERY POINT", 1, 2]]
    row = parse_chart(workbook_bytes(("Chart", rows)), "u.xlsx").measurements[0]
    assert (row["key"], row["mapping_status"], row["mapped_from"]) == ("Z9", "unmapped", None)


def test_a_style_description_label_is_not_taken_as_the_table_header():
    style = ["STYLE DESCRIPTION :", "pant", 1, 2]
    rows = [style, [None, None, 3, 4], [None, None, 5, 6], HEADER, *ROWS]
    chart = parse_chart(workbook_bytes(("Chart", rows)), "style.xlsx")
    assert (chart.header_row, chart.sizes) == (4, ("4", "4½", "5"))
