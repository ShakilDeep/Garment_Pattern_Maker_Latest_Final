"""Draft a pattern with a block: resolve style choices, draft the base, then apply the option transforms."""
from collections.abc import Mapping

from app.domain.blocks.base import Block, NamedBlock, Pieces
from app.domain.blocks.options import resolve_choices
from app.domain.blocks.sketch.naming import check_named
from app.domain.blocks.transforms import TransformPipeline


def draft_pattern(
    block: Block, measurements: Mapping[str, float], size: str, requested: Mapping[str, str]
) -> dict:
    """The V5 pattern dict that V5 grading, markers and exports read (the demo shirt today)."""
    if isinstance(block, NamedBlock):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"Block {block.id} drafts named V6 pieces only; V5 exports arrive with T130/T131")  # noqa: TRY004
    choices = resolve_choices(block, requested)
    pattern = block.draft(measurements, size, choices)
    return TransformPipeline(block.transforms).apply(pattern, choices)


def draft_named(
    block: NamedBlock, measurements: Mapping[str, float], size: str, requested: Mapping[str, str]
) -> Pieces:
    """Named V6 pieces; a client block's every point must carry a drafting name, after its transforms too."""
    choices = resolve_choices(block, requested)
    pieces = TransformPipeline(block.transforms).apply(block.draft_pieces(measurements, size, choices), choices)
    if block.calibration == "client_approved":  # demo blocks may draft unnamed points until promoted
        for piece in pieces:
            check_named(piece)
    return pieces
