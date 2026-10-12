"""Where each input of a named block comes from, per size (T142, Chain of Responsibility per input).

1. A confirmed chart-map entry whose chart row is mapped and has a value for the size (`chart:<pom>`).
2. Else, once the user has accepted the block's reference values, the reference block's own value for
   the size (`from_block`); the 1078375 block's are derived from the client PDS, sizes S–3XL.
3. Else the input is missing: Missing Information asks for it, nothing is guessed.
A block with a chart grader (T145) grades a size that has chart values from them instead: followers and pair
partners move with the chart and the seams are trued again, and every value says where it came from.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.application.cad.style_from_block import ReferenceBlock
from app.application.pattern_inputs import drafting_values
from app.domain.blocks.base import Block, BlockInfo, NamedBlock
from app.domain.blocks.chart_map import CONFIRMED, chart_map
from app.domain.blocks.shirt.chart_grade import CHART, FROM_BLOCK, ChartGraded, grade_from_chart

REFERENCE_KEY, ACCEPTED = "block_reference", "accepted"
CHART_GRADERS: Mapping[str, Callable[[str, Mapping[str, float]], ChartGraded]] = {
    "shirt_1078375": grade_from_chart,
}


@dataclass(frozen=True)
class BlockInputs:
    values: Mapping[str, float]
    sources: Mapping[str, str]
    missing: tuple[str, ...]


def _reference(project: dict, block: BlockInfo, size: str) -> Mapping[str, float]:
    accepted = project["resolutions"].get(REFERENCE_KEY) == ACCEPTED
    if accepted and isinstance(block, ReferenceBlock) and size in block.graded_sizes():
        return block.graded_measurements(size)
    return {}


def block_inputs(project: dict, block: BlockInfo, size: str) -> BlockInputs:
    chart = drafting_values(project, size)
    mapped = {entry.input: entry.pom for entry in chart_map(block) if entry.status == CONFIRMED}
    reference = _reference(project, block, size)
    from_chart = {name: pom for name, pom in mapped.items() if pom in chart}
    grader = CHART_GRADERS.get(block.id)
    if from_chart and reference and grader is not None:
        return _chart_graded(grader(size, {name: chart[pom] for name, pom in from_chart.items()}), from_chart)
    values: dict[str, float] = {}
    sources: dict[str, str] = {}
    for name in block.required:
        pom = mapped.get(name)
        if pom is not None and pom in chart:
            values[name], sources[name] = chart[pom], f"chart:{pom}"
        elif name in reference:
            values[name], sources[name] = reference[name], FROM_BLOCK
    return BlockInputs(values, sources, tuple(name for name in block.required if name not in values))


def _chart_graded(graded: ChartGraded, poms: Mapping[str, str]) -> BlockInputs:
    sources = {name: f"chart:{poms[name]}" if source == CHART else source for name, source in graded.sources.items()}
    return BlockInputs(graded.values, sources, ())


def draft_values(project: dict, block: Block, size: str) -> tuple[dict[str, float], Mapping[str, str] | None]:
    """The values a block drafts from, and for a named block where each came from (the From-block list)."""
    if isinstance(block, NamedBlock):
        inputs = block_inputs(project, block, size)
        return dict(inputs.values), inputs.sources
    values = drafting_values(project, size)
    if project["resolutions"].get("placket") == "techpack":
        values["front_placket_width"] = project["techpack"]["placket_cm"]
    return values, None
