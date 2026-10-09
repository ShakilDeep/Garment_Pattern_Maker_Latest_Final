"""Draft a pattern with a block: resolve style choices, draft the base, then apply the option transforms."""
from collections.abc import Mapping

from app.domain.blocks.base import Block
from app.domain.blocks.options import resolve_choices
from app.domain.blocks.transforms import TransformPipeline


def draft_pattern(block: Block, measurements: Mapping[str, float], size: str, requested: Mapping[str, str]) -> dict:
    choices = resolve_choices(block, requested)
    pattern = block.draft(measurements, size, choices)
    return TransformPipeline(block.transforms).apply(pattern, choices)
