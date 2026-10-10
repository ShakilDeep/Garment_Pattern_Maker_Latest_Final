"""The 1078375 block's measurements: each is defined on the PDS sew line (docs/drafting/shirt.md, size L).

A definition reads one axis between two named points of one piece: value = coordinate(b) - coordinate(a),
in cm along x (the fabric length) or y. The derivation (``infrastructure/pds/shirt_derive``) applies these
to the client PDS; the block only reads the values by name.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.domain.blocks.shirt.body import BACK, FRONT, YOKE
from app.domain.blocks.shirt.parts import BAND_IN, BAND_TOP, COLLAR, SLEEVE
from app.domain.blocks.shirt.recipe import PieceRecipe
from app.domain.pattern.point import is_real

RECIPES: tuple[PieceRecipe, ...] = (FRONT, BACK, YOKE, COLLAR, BAND_TOP, BAND_IN, SLEEVE)


@dataclass(frozen=True)
class Definition:
    piece: str
    start: str
    end: str
    axis: Literal["x", "y"]


def _d(piece: str, start: str, end: str, axis: Literal["x", "y"]) -> Definition:
    return Definition(piece, start, end, axis)


DEFINITIONS: Mapping[str, Definition] = {
    "front_length": _d("FRT", "FE_hem", "HPS", "x"),
    "front_neck_width": _d("FRT", "CF_neck", "HPS", "y"),
    "front_neck_drop": _d("FRT", "CF_neck", "HPS", "x"),
    "placket_rise": _d("FRT", "CF_neck", "CF_top", "x"),
    "front_extension": _d("FRT", "FE_top", "CF_top", "y"),
    "front_shoulder_drop": _d("FRT", "SP", "HPS", "x"),
    "front_shoulder_width": _d("FRT", "HPS", "SP", "y"),
    "front_armhole_depth": _d("FRT", "UA", "SP", "x"),
    "half_chest_front": _d("FRT", "CF_neck", "UA", "y"),
    "front_hem_width": _d("FRT", "CF_neck", "side_hem", "y"),
    "back_length": _d("back", "CB_hem", "CB_yoke", "x"),
    "back_yoke_drop": _d("back", "yoke_armhole", "CB_yoke", "x"),
    "back_yoke_width": _d("back", "CB_yoke", "yoke_armhole", "y"),
    "back_armhole_depth": _d("back", "UA", "yoke_armhole", "x"),
    "half_chest_back": _d("back", "CB_hem", "UA", "y"),
    "back_hem_width": _d("back", "CB_hem", "side_hem", "y"),
    "yoke_depth_cb": _d("back_YK", "CB_yoke", "CB_neck", "x"),
    "back_neck_rise": _d("back_YK", "CB_neck", "HPS", "x"),
    "back_neck_width": _d("back_YK", "CB_neck", "HPS", "y"),
    "yoke_shoulder_drop": _d("back_YK", "SP", "HPS", "x"),
    "across_back_half": _d("back_YK", "CB_yoke", "SP", "y"),
    "yoke_seam_width": _d("back_YK", "CB_yoke", "yoke_armhole", "y"),
    "collar_width_cb": _d("CLR", "CB_collar_neck", "CB_collar_outer", "y"),
    "collar_length": _d("CLR", "CB_collar_neck", "collar_point", "x"),
    "collar_neck_reach": _d("CLR", "CB_collar_neck", "collar_neck_end", "x"),
    "collar_point_rise": _d("CLR", "CB_collar_neck", "collar_point", "y"),
    "band_height_cb": _d("BND_TOP", "CB_band_top", "CB_band_neck", "y"),
    "band_length": _d("BND_TOP", "CB_band_top", "band_neck_end", "x"),
    "band_top_reach": _d("BND_TOP", "CB_band_top", "band_top_end", "x"),
    "underarm_height": _d("Sleeve", "hem_front", "UA_front", "x"),
    "bicep": _d("Sleeve", "UA_back", "UA_front", "y"),
    "cap_height": _d("Sleeve", "UA_front", "cap_crown", "x"),
    "cap_front_width": _d("Sleeve", "cap_crown", "UA_front", "y"),
    "hem_turnup": _d("Sleeve", "hem_front", "hem_fold_front", "x"),
    "sleeve_hem_width": _d("Sleeve", "hem_back", "hem_front", "y"),
}
REQUIRED: tuple[str, ...] = tuple(DEFINITIONS)


def require(measures: Mapping[str, float]) -> dict[str, float]:
    """The block's measurements; a missing, non-finite or non-positive one is a ValueError naming them all."""
    bad = sorted(name for name in REQUIRED if not is_real(measures.get(name)) or not measures[name] > 0)
    if bad:
        raise ValueError(f"Missing or non-positive shirt measurements: {', '.join(bad)}")
    return {name: float(measures[name]) for name in REQUIRED}
