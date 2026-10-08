"""Detect a graded chart's base size from how the workbook is built, never from the values.

In a formula-graded chart the base column holds typed numbers and the other sizes are formulas off it.
Only rows with at least one formula are evidence; the base is the one size column that is typed in all
of them. No formulas, or more than one such column, means the base size is unknown (asked, not guessed).
"""
from collections.abc import Iterable, Mapping


def detect_base(sheet, size_cols: Mapping[str, int], rows: Iterable[int]) -> str | None:
    graded = [row for row in rows if any(sheet.cell(row, col).data_type == "f" for col in size_cols.values())]
    if not graded:
        return None
    typed = [
        size for size, col in size_cols.items()
        if all(sheet.cell(row, col).data_type != "f" and sheet.cell(row, col).value is not None
               for row in graded)
    ]
    return typed[0] if len(typed) == 1 else None
