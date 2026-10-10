"""Seam allowance of each 1078375 piece: every edge takes its confirmed finishing role (``finishing.json``).

Every edge is listed explicitly, so no edge falls back to a default width; fold edges take the family's fold
width (0). Corners keep the default mitre, the shirt family's corner setting.
"""
from functools import cache

from app.domain.blocks.shirt.measures import RECIPES
from app.domain.blocks.sketch.naming import segment_id
from app.domain.finishing import allowance, finishing
from app.domain.pattern.seam import SeamAllowance

FAMILY = "shirt"


@cache
def seam_allowance(piece_id: str) -> SeamAllowance:
    recipe = next((r for r in RECIPES if r.id == piece_id), None)
    if recipe is None:
        raise KeyError(f"The 1078375 block has no piece {piece_id}")
    fold = finishing().families[FAMILY].fold_edge_cm
    widths = tuple(
        (segment_id(start, end), fold if role == "fold" else allowance(FAMILY, role).value_cm)
        for (start, end), role in zip(recipe.edges(), recipe.roles, strict=True)
    )
    return SeamAllowance(0.0, widths)
