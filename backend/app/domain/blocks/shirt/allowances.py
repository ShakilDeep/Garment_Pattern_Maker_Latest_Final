"""Seam allowance of each 1078375 piece: every edge takes its confirmed finishing role (``finishing.json``).

Every edge is listed explicitly, so no edge falls back to a default width; fold edges take the family's fold
width (0). Every corner takes the family's corner style from finishing.json (mitre, pattern maker to confirm).
"""
from functools import cache

from app.domain.blocks.shirt.measures import RECIPES
from app.domain.blocks.sketch.naming import segment_id
from app.domain.finishing import allowance, finishing
from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.ids import PointId
from app.domain.pattern.seam import SeamAllowance

FAMILY = "shirt"


@cache
def seam_allowance(piece_id: str) -> SeamAllowance:
    recipe = next((r for r in RECIPES if r.id == piece_id), None)
    if recipe is None:
        raise KeyError(f"The 1078375 block has no piece {piece_id}")
    family = finishing().families[FAMILY]
    fold, corner = family.fold_edge_cm, CornerStyle(family.corner)
    widths = tuple(
        (segment_id(start, end), fold if role == "fold" else allowance(FAMILY, role).value_cm)
        for (start, end), role in zip(recipe.edges(), recipe.roles, strict=True)
    )
    corners = tuple((PointId(start), corner) for start, _ in recipe.edges())
    return SeamAllowance(0.0, widths, corners)
