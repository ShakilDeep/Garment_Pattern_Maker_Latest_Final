"""Missing Information for the measurements a project's drafting block needs (T142).

A dict block needs the chart's catalog POMs, each asked for when missing or not positive. A named block's
inputs that the chart does not give through a confirmed mapping are one question: may the block's own
reference values be used ("From block")? Inputs that even the reference cannot give (a size outside the
reference range) are each asked for by name. Every answer is recorded; nothing is filled in silently.
"""
from collections.abc import Callable

from app.application.block_inputs import ACCEPTED, FROM_BLOCK, REFERENCE_KEY, block_inputs
from app.domain.blocks.base import BlockInfo, NamedBlock
from app.domain.blocks.registry import demo_block, installed
from app.domain.catalog import REQUIRED

Add = Callable[..., None]  # requirements()' item builder: add(key, name, status, why, options)


def block_items(project: dict, block: BlockInfo, size: str, add: Add) -> None:
    inputs = block_inputs(project, block, size)
    from_chart = sum(1 for source in inputs.sources.values() if source != FROM_BLOCK)
    unmapped = len(block.required) - from_chart
    if unmapped:
        accepted = project["resolutions"].get(REFERENCE_KEY) == ACCEPTED
        add(REFERENCE_KEY, f"Use the {block.id} reference values", "AVAILABLE" if accepted else "MISSING",
            f"{unmapped} of {len(block.required)} block measurements have no confirmed chart mapping. "
            "Accept the block's reference values for them; each is listed as From block.", [ACCEPTED])
        if not accepted:
            return
    for name in inputs.missing:
        add("measurement:" + name, name.replace("_", " ").title(), "MISSING",
            f"No chart value or reference value exists for {name} at size {size}. Enter it in cm.", [])


def _catalog_items(project: dict, size: str, add: Add) -> None:
    rows = {row["key"]: row for row in project["measurements"]}
    for key in REQUIRED:
        value = rows.get(key, {}).get("values", {}).get(size, {}).get("value")
        if value is None or value <= 0:
            add("measurement:" + key, key.replace("_", " ").title(), "MISSING",
                f"Enter a positive {size} value in cm in the measurement editor.", [])


def measurement_items(project: dict, size: str, add: Add) -> None:
    block = installed().get(project["resolutions"].get("profile", demo_block().id))
    if isinstance(block, NamedBlock):
        block_items(project, block, size, add)
    else:
        _catalog_items(project, size, add)
