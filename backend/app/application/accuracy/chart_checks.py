"""Chart checks (spec §0.1): every block input drafted from a chart POM, measured back on the drafted sew line,
is within that POM's chart tolerance in every drafted size.

Which inputs came from the chart is what each pattern recorded (`input_sources`, `chart:<pom>`, T142). A chart
row without a tolerance fails: the limit is missing information and is never guessed. The chart's tolerance
column stays in the chart's own unit, so it is converted to cm as the row's values were (T146).
"""
from collections.abc import Iterator, Mapping
from dataclasses import replace

from app.application.accuracy.model import Check, Source, at_size
from app.domain.blocks.shirt.measures import Definition
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style
from app.domain.tolerances import COORDINATE
from app.domain.units import to_cm

CHART = "chart:"
NO_TOLERANCE = "chart gives no tolerance"


def measured(definition: Definition, piece: Piece) -> float:
    start, end = piece.point(PointId(definition.start)).position, piece.point(PointId(definition.end)).position
    return end.x - start.x if definition.axis == "x" else end.y - start.y


def chart_inputs(project: dict) -> Iterator[tuple[str, str, str]]:
    """(size, input, POM) for every input a drafted size took from the chart."""
    for pattern in (project.get("pattern"), *project.get("grades", [])):
        for name, source in ((pattern or {}).get("input_sources") or {}).items():
            if source.startswith(CHART):
                yield pattern["size"], name, source.removeprefix(CHART)


def _check(name: str, value: float, row: dict, target_and_tolerance: tuple[float, float | None]) -> Check:
    target, tolerance = target_and_tolerance
    source = Source("chart", f"chart row {row['row']} ({row['key']}), tolerance column")
    if tolerance is None:
        return Check(name, value, NO_TOLERANCE, False, source)
    passed = abs(value - target) <= tolerance + COORDINATE
    return Check(name, value, f"{target:.3f} ± {tolerance} cm", passed, source)


def _tolerance_cm(row: dict, fact: Mapping) -> float | None:
    tolerance = fact.get("tolerance")
    return None if tolerance is None else to_cm(tolerance, row.get("source_unit", "cm"))


def chart_checks(project: dict, style: Style, definitions: Mapping[str, Definition]) -> list[Check]:
    rows = {row["key"]: row for row in project.get("measurements", [])}
    facts = {fact["ref"]: fact for fact in (project.get("chart") or {}).get("rows", [])}
    checks = []
    for size, name, pom in chart_inputs(project):
        if not style.has_geometry(size):
            continue
        definition, row = definitions[name], rows[pom]
        piece = next(p for p in style.view(size) if str(p.id) == definition.piece)
        limit = (row["values"][size]["value"], _tolerance_cm(row, facts.get(str(row["row"]), {})))
        check = at_size(_check(f"{name} (chart {pom})", measured(definition, piece), row, limit), size)
        checks.append(replace(check, piece=piece.name, edge=f"{definition.start}:{definition.end}"))
    return checks
