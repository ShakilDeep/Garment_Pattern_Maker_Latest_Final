"""Find the POM × size table in a spec workbook, on any sheet and with any size labels.

A header row has a description column (MEASUREMENT / DESCRIPTION / POINT) and at least two size
columns to its right. A header cell counts as a size only when the rows below it hold numbers or
formulas, so labels such as XS, 32 or 4½ work without a fixed list. The sheet whose table has the most
size columns wins; on a tie, the first sheet.
"""
import re
from dataclasses import dataclass

from app.domain.pom_labels import size_label
from app.infrastructure.formulas import number

HEADER_SCAN_ROWS = 30
SIZE_PROBE_ROWS = 3
MAX_SIZE_LABEL = 8
MIN_SIZE_COLUMNS = 2
_DESCRIPTION = re.compile(r"MEASUREMENT|(?<!STYLE )DESCRIPTION|\bPOINTS?\b", re.IGNORECASE)
_CODE = re.compile(r"^(POM|CODES?|POM CODE)$", re.IGNORECASE)
_NOT_SIZE = re.compile(r"TOL|GRADE|CODE|COMMENT|POM", re.IGNORECASE)
_UNIT = re.compile(r"\b(CM|INCH)(ES)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class TableLayout:
    sheet: str
    header_row: int
    code_col: int
    label_col: int
    alt_col: int | None
    size_cols: dict[str, int]
    tolerance_col: int | None
    unit_hint: str | None


def _numeric(cell) -> bool:
    if cell.data_type == "f":
        return True
    try:
        number(cell.value)
    except (ValueError, TypeError):
        return False
    return True


def _probe(sheet, row: int, col: int, test) -> bool:
    return any(test(sheet.cell(row + offset, col)) for offset in range(1, SIZE_PROBE_ROWS + 1))


def _size_cols(sheet, header, label_col: int) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for cell in header:
        label = size_label(cell.value) if cell.value not in (None, "") else ""
        if cell.column <= label_col or not label or len(label) > MAX_SIZE_LABEL or _NOT_SIZE.search(label):
            continue
        if _probe(sheet, cell.row, cell.column, _numeric):
            if label in sizes:
                raise ValueError(f"Duplicate size label {label} on sheet {sheet.title!r}")
            sizes[label] = cell.column
    return sizes


def _layout(sheet, header) -> TableLayout | None:
    texts = {cell.column: str(cell.value).strip() for cell in header if cell.value not in (None, "")}
    label_col = next((col for col, text in texts.items() if _DESCRIPTION.search(text)), None)
    if label_col is None:
        return None
    sizes = _size_cols(sheet, header, label_col)
    if len(sizes) < MIN_SIZE_COLUMNS:
        return None
    row = header[0].row
    alt_col = next((col for col in range(label_col + 1, min(sizes.values()))
                    if _probe(sheet, row, col, lambda cell: isinstance(cell.value, str))), None)
    unit = next((found[1].lower() for text in texts.values() if (found := _UNIT.search(text))), None)
    return TableLayout(
        sheet=sheet.title,
        header_row=row,
        code_col=next((col for col, text in texts.items() if _CODE.match(text)), 1),
        label_col=label_col,
        alt_col=alt_col,
        size_cols=sizes,
        tolerance_col=next((col for col, text in texts.items() if "TOLERANCE" in text.upper()), None),
        unit_hint=unit,
    )


def find_table(book) -> TableLayout | None:
    layouts = []
    for sheet in book:
        rows = sheet.iter_rows(max_row=min(sheet.max_row, HEADER_SCAN_ROWS))
        layout = next((found for header in rows if (found := _layout(sheet, header))), None)
        if layout:
            layouts.append(layout)
    return max(layouts, key=lambda layout: len(layout.size_cols), default=None)
