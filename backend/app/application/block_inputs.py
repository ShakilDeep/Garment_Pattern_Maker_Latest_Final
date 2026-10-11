"""Where each input of a named block comes from, per size (T142, Chain of Responsibility per input).

1. A confirmed chart-map entry whose chart row is mapped and has a value for the size (`chart:<pom>`).
2. Else, once the user has accepted the block's reference values, the reference block's own value for
   the size (`from_block`); the 1078375 block's are derived from the client PDS, sizes S–3XL.
3. Else the input is missing: Missing Information asks for it, nothing is guessed.
"""
from collections.abc import Mapping
from dataclasses import dataclass

from app.application.cad.style_from_block import ReferenceBlock
from app.application.pattern_inputs import drafting_values
from app.domain.blocks.base import Block, BlockInfo, NamedBlock
from app.domain.blocks.chart_map import CONFIRMED, chart_map

REFERENCE_KEY, ACCEPTED, FROM_BLOCK = "block_reference", "accepted", "from_block"


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
    values: dict[str, float] = {}
    sources: dict[str, str] = {}
    for name in block.required:
        pom = mapped.get(name)
        if pom is not None and pom in chart:
            values[name], sources[name] = chart[pom], f"chart:{pom}"
        elif name in reference:
            values[name], sources[name] = reference[name], FROM_BLOCK
    return BlockInputs(values, sources, tuple(name for name in block.required if name not in values))


def draft_values(project: dict, block: Block, size: str) -> tuple[dict[str, float], Mapping[str, str] | None]:
    """The values a block drafts from, and for a named block where each came from (the From-block list)."""
    if isinstance(block, NamedBlock):
        inputs = block_inputs(project, block, size)
        return dict(inputs.values), inputs.sources
    values = drafting_values(project, size)
    if project["resolutions"].get("placket") == "techpack":
        values["front_placket_width"] = project["techpack"]["placket_cm"]
    return values, None
