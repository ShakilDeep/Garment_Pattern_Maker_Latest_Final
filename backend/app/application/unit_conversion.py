"""Command helper: rescale workbook values to centimetres once the user confirms the workbook unit."""
from app.domain.units import to_cm


def apply_workbook_unit(project: dict, unit: str) -> None:
    """Convert every workbook cell and numeric tolerance from `unit` to cm.

    The as-read number is kept (`unit_source_value`, `tolerance_source`) and every conversion starts from it,
    so confirming cm -> inch -> cm restores the original values exactly. Manual overrides are entered in cm
    and are never rescaled.
    """
    for row in project["measurements"]:
        row["unit"], row["source_unit"] = "cm", unit
        for cell in row["values"].values():
            _convert_cell(cell, unit)
        _convert_tolerance(row, unit)


def _convert_cell(cell: dict, unit: str) -> None:
    if cell.get("override"):
        return
    source = cell.setdefault("unit_source_value", cell.get("value"))
    if source is not None:
        cell["value"] = to_cm(source, unit)


def _convert_tolerance(row: dict, unit: str) -> None:
    source = row.setdefault("tolerance_source", row.get("tolerance"))
    if isinstance(source, (int, float)) and not isinstance(source, bool):
        row["tolerance"] = to_cm(source, unit)
