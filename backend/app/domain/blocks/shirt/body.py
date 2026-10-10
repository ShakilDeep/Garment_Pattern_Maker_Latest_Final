"""Recipes for the 1078375 body pieces: FRT (front), back and back YK (yoke), as in docs/drafting/shirt.md."""
from app.domain.blocks.shirt.recipe import NotchRecipe, PieceRecipe, at

_CF_TOP_X = {"front_length": 1, "front_neck_drop": -1, "placket_rise": 1}
_FRONT_SP_X = {"front_length": 1, "front_shoulder_drop": -1}
_BACK_ARMHOLE_X = {"back_length": 1, "back_yoke_drop": -1}
_YOKE_HPS_X = {"yoke_depth_cb": 1, "back_neck_rise": 1}

FRONT = PieceRecipe(
    "FRT", "FRT", (0, 1, 0), ("FE_hem", "CF_neck"),
    (
        at("FE_top", _CF_TOP_X, {"front_extension": -1}),
        at("CF_top", _CF_TOP_X, {}),
        at("CF_neck", {"front_length": 1, "front_neck_drop": -1}, {}),
        at("HPS", {"front_length": 1}, {"front_neck_width": 1}),
        at("SP", _FRONT_SP_X, {"front_neck_width": 1, "front_shoulder_width": 1}),
        at("UA", {**_FRONT_SP_X, "front_armhole_depth": -1}, {"half_chest_front": 1}),
        at("side_hem", {}, {"front_hem_width": 1}),
        at("FE_hem", {}, {"front_extension": -1}),
    ),
    ("line", "line", "cubic", "line", "cubic", "cubic", "cubic", "line"),
    ("placket_top", "placket_cf_step", "neckline", "shoulder", "armhole_body", "side_seam_front", "hem", "front_edge"),
)

BACK = PieceRecipe(
    "back", "back", (0, 0, 1), ("CB_hem", "CB_hem"),
    (
        at("CB_yoke", {"back_length": 1}, {}),
        at("yoke_armhole", _BACK_ARMHOLE_X, {"back_yoke_width": 1}),
        at("UA", {**_BACK_ARMHOLE_X, "back_armhole_depth": -1}, {"half_chest_back": 1}),
        at("side_hem", {}, {"back_hem_width": 1}),
        at("CB_hem", {}, {}),
    ),
    ("cubic", "cubic", "cubic", "cubic", "line"),
    ("yoke_seam", "armhole_body", "side_seam_back", "hem", "fold"),
)

YOKE = PieceRecipe(
    "back_YK", "back YK", (0, 0, 2), ("CB_yoke", "CB_yoke"),
    (
        at("CB_neck", {"yoke_depth_cb": 1}, {}),
        at("HPS", _YOKE_HPS_X, {"back_neck_width": 1}),
        at("SP", {**_YOKE_HPS_X, "yoke_shoulder_drop": -1}, {"across_back_half": 1}),
        at("yoke_armhole", {}, {"yoke_seam_width": 1}),
        at("CB_yoke", {}, {}),
    ),
    ("cubic", "line", "cubic", "line", "line"),
    ("neckline", "shoulder", "armhole_body", "yoke_seam", "fold"),
    (NotchRecipe("shoulder_notch", "HPS", "SP"),),
)
