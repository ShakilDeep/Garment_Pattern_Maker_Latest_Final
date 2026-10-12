"""Missing Information for a confirmed style variant the drafting block has no source for (T147).

No client file gives short-sleeve POMs for the chart-driven shirts or a pocket for any shirt, so such a choice is
a blocking question: nothing is drafted for it and no answer fills it in. The user supplies a source or confirms
a style the block drafts. ``unknown`` is never asked about.
"""
from collections.abc import Mapping

from app.application.chart_requirements import requirement_item
from app.domain.style_detect.schema import UNKNOWN

_LONG_NO_POCKET = {"sleeve": ("long",), "pockets": ("none",)}
# The style-detect values each block drafts (domain/style_detect/schema.py vocabulary).
DRAFTS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "demo_v1": _LONG_NO_POCKET,
    "shirt_v2": _LONG_NO_POCKET,
    "shirt_1078375": {"sleeve": ("short",), "pockets": ("none",)},
}


def style_items(project: dict, block_id: str) -> list[dict]:
    chosen = (project.get("style_choices") or {}).get("options", {})
    drafted = DRAFTS.get(block_id, {})
    return [
        {**requirement_item(f"style:{option}", f"{option.title()}: {value}", "MISSING",
                            f"The confirmed style has {option} '{value}', but no client source gives that "
                            f"variant for {block_id}. Supply its source or confirm a style {block_id} drafts.",
                            [], project),
         "blocking": True, "category": "Drafting rules", "source": "Confirmed style"}
        for option, values in drafted.items()
        if (value := chosen.get(option, UNKNOWN)) not in (*values, UNKNOWN)
    ]
