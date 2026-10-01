"""Plausible range per measurement, derived from its own source-chart values (no hand-picked garment numbers)."""

BLANKET_MAX_CM = 500
SOURCE_LOW_FACTOR = 0.5
SOURCE_HIGH_FACTOR = 1.5


def _real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def keep_source_value(cell):
    """Before a cell's first override, remember the evaluated source value (formula cells keep only text in `raw`)."""
    if not cell.get("override"):
        cell.setdefault("source_value", cell.get("value"))


def _source_value(cell):
    if "source_value" in cell:
        return cell["source_value"]
    return cell.get("raw") if cell.get("override") else cell.get("value")


def source_values(row):
    """Positive values the source supplied, independent of later overrides."""
    values = [_source_value(cell) for cell in row.get("values", {}).values()]
    return [value for value in values if _real(value) and value > 0]


def plausible_range(row):
    values = source_values(row)
    if not values:
        return 0, BLANKET_MAX_CM
    return min(values) * SOURCE_LOW_FACTOR, min(max(values) * SOURCE_HIGH_FACTOR, BLANKET_MAX_CM)


def accepts(row, value):
    low, high = plausible_range(row)
    return 0 < value <= BLANKET_MAX_CM and low <= value <= high
