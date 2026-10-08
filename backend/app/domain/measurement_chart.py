"""A buyer's measurement chart (POM × size table) as imported from a spec workbook.

``measurements`` keeps the legacy row shape that drafting, edits and the 1078983 goldens rely on;
the chart-level facts (sizes, base size, half flags, numeric tolerances) live beside it.
"""
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ChartRow:
    """Per-row facts that are not part of the legacy row; ``ref`` is the source row number."""

    ref: str
    half: bool
    tolerance: float | None
    alt_label: str | None


@dataclass(frozen=True)
class MeasurementChart:
    sheet: str
    header_row: int
    sizes: tuple[str, ...]
    base_size: str | None
    unit_hint: str | None
    rows: tuple[ChartRow, ...]
    measurements: list[dict] = field(compare=False)
    meta: Mapping[str, str] = field(default_factory=dict)
    issues: tuple[str, ...] = ()

    def to_project(self) -> dict:
        """JSON-ready chart facts stored on the project next to its measurement rows."""
        return {
            "parser_version": "pom_import_v1",
            "sheet": self.sheet,
            "header_row": self.header_row,
            "sizes": list(self.sizes),
            "base_size": self.base_size,
            "unit_hint": self.unit_hint,
            "meta": dict(self.meta),
            "issues": list(self.issues),
            "rows": [asdict(row) for row in self.rows],
        }
