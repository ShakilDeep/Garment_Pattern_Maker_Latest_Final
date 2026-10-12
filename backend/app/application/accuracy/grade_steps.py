"""Grade steps (spec §7 Grading, T145): between consecutive drafted sizes, every chart-sourced input's drafted
step, measured on the sew line, equals the chart's own step within 0.1 cm."""
from collections.abc import Mapping
from itertools import pairwise

from app.application.accuracy.chart_checks import chart_inputs, measured
from app.application.accuracy.model import Check, Source
from app.domain.blocks.shirt.measures import Definition
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style

STEP_CM = 0.1  # spec §7: POM steps equal chart steps within 0.1 cm

Named = tuple[str, Definition]  # block input and how it is measured


def _piece(style: Style, size: str, definition: Definition) -> Piece:
    return next(p for p in style.view(size) if str(p.id) == definition.piece)


def _step(style: Style, sizes: tuple[str, str], input_: Named, row: dict) -> Check:
    (a, b), (name, definition) = sizes, input_
    pieces = _piece(style, a, definition), _piece(style, b, definition)
    drafted = measured(definition, pieces[1]) - measured(definition, pieces[0])
    chart = row["values"][b]["value"] - row["values"][a]["value"]
    source = Source("chart", f"chart row {row['row']} ({row['key']}), steps between sizes")
    return Check(f"{a}→{b} {name} step (chart {row['key']})", drafted, f"{chart:+.3f} ± {STEP_CM} cm",
                 abs(drafted - chart) <= STEP_CM, source, size=b, piece=pieces[1].name,
                 edge=f"{definition.start}:{definition.end}")


def grade_step_checks(project: dict, style: Style, definitions: Mapping[str, Definition]) -> list[Check]:
    rows = {row["key"]: row for row in project.get("measurements", [])}
    charted: dict[tuple[str, str], set[str]] = {}
    for size, name, pom in chart_inputs(project):
        charted.setdefault((name, pom), set()).add(size)
    checks = []
    for (name, pom), sizes in charted.items():
        drafted = [size for size in style.sizes if size in sizes and style.has_geometry(size)]
        checks += [_step(style, pair, (name, definitions[name]), rows[pom]) for pair in pairwise(drafted)]
    return checks
