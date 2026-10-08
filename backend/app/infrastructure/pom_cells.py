"""Read one size cell: safe formula evaluation first, Excel's cached result as the fallback.

The order and issue texts are the 1078983 golden contract; a value that cannot be read is None with an
issue, never a guess.
"""
from app.infrastructure.formulas import cell_value, number

UNRESOLVED = "Unresolved numeric value or unsupported formula"
CACHED = "Cached Excel result; confirm source review before use"


def read_cell(sheet, cached_sheet, row: int, col: int) -> dict:
    cell = sheet.cell(row, col)
    is_formula = cell.data_type == "f"
    evaluation = "formula" if is_formula else "direct"
    try:
        value, issue = cell_value(sheet, cell.coordinate), None
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError):
        value, issue = None, UNRESOLVED
        if is_formula:
            try:
                value = number(cached_sheet[cell.coordinate].value)
                issue, evaluation = CACHED, "cached"
            except (ValueError, TypeError):
                pass
    return {
        "value": value,
        "raw": cell.value,
        "formula": cell.value if is_formula else None,
        "cell": cell.coordinate,
        "issue": issue,
        "override": False,
        "evaluation": evaluation,
    }
