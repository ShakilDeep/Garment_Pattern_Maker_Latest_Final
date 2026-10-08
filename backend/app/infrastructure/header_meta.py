"""Read the style block above a POM table (style number, description, size range, fit).

A declared size range that disagrees with the table's size columns is reported as an issue; neither
side is corrected.
"""
from collections.abc import Sequence

from app.domain.pom_labels import normalize

LABELS = {"STYLE#": "style", "STYLE DESCRIPTION": "description", "SIZE / RANGE": "size_range",
          "BASE PATTERN / FIT": "fit"}


def _value_after(row, index: int) -> str | None:
    """First value right of a label; reaching the next label first means the value is absent."""
    for cell in row[index + 1:]:
        if cell.value not in (None, ""):
            return None if normalize(cell.value) in LABELS else str(cell.value).strip()
    return None


def read_meta(sheet, header_row: int) -> dict[str, str]:
    """Pass the cached-values sheet: style cells are often formulas pointing at another sheet."""
    meta: dict[str, str] = {}
    for row in sheet.iter_rows(max_row=header_row - 1):
        for index, cell in enumerate(row):
            field = LABELS.get(normalize(cell.value))
            value = _value_after(row, index) if field else None
            if field and value and field not in meta:
                meta[field] = value
    return meta


def range_issues(meta: dict[str, str], sizes: Sequence[str]) -> tuple[str, ...]:
    declared = [part.strip().upper() for part in meta.get("size_range", "").split("/") if part.strip()]
    if len(declared) != 2 or not sizes:
        return ()
    table = (sizes[0].upper(), sizes[-1].upper())
    if tuple(declared) == table:
        return ()
    issue = f"The header declares size range {declared[0]}–{declared[1]} but the table has {sizes[0]}–{sizes[-1]}"
    return (issue,)
