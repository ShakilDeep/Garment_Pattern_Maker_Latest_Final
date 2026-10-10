"""Recipes for the 1078375 collar (CLR), the two band pieces (BND TOP, BND IN) and the Sleeve (docs/drafting/shirt.md)."""
from app.domain.blocks.shirt.recipe import EdgeKind, NotchRecipe, PieceRecipe, PointRecipe, at

COLLAR = PieceRecipe(
    "CLR", "CLR", (0, 0, 2), ("CB_collar_neck", "CB_collar_neck"),
    (
        at("CB_collar_neck", {}, {}),
        at("collar_neck_end", {"collar_neck_reach": 1}, {}),
        at("collar_point", {"collar_length": 1}, {"collar_point_rise": 1}),
        at("CB_collar_outer", {}, {"collar_width_cb": 1}),
    ),
    ("cubic", "line", "cubic", "line"),
    ("collar", "collar", "collar", "fold"),
)

_BAND_POINTS: tuple[PointRecipe, ...] = (
    at("CB_band_top", {}, {}),
    at("band_top_end", {"band_top_reach": 1}, {}),
    at("band_neck_end", {"band_length": 1}, {}),
    at("CB_band_neck", {}, {"band_height_cb": 1}),
)
_BAND_KINDS: tuple[EdgeKind, ...] = ("cubic", "cubic", "cubic", "line")
_BAND_ROLES = ("collar_band", "collar_band", "collar_band", "fold")
_BAND_ORIGIN = ("CB_band_top", "CB_band_top")
BAND_TOP = PieceRecipe("BND_TOP", "BND TOP", (0, 0, 1), _BAND_ORIGIN, _BAND_POINTS, _BAND_KINDS, _BAND_ROLES)
BAND_IN = PieceRecipe("BND_IN", "BND IN", (0, 0, 1), _BAND_ORIGIN, _BAND_POINTS, _BAND_KINDS, _BAND_ROLES)

_HEM_FRONT_Y = {"bicep": -0.5, "sleeve_hem_width": 0.5}
_HEM_BACK_Y = {"bicep": -0.5, "sleeve_hem_width": -0.5}

SLEEVE = PieceRecipe(
    "Sleeve", "Sleeve", (0, 1, 0), ("hem_front", "UA_front"),
    (
        at("hem_fold_back", {"hem_turnup": 1}, _HEM_BACK_Y),
        at("UA_back", {"underarm_height": 1}, {"bicep": -1}),
        at("cap_crown", {"underarm_height": 1, "cap_height": 1}, {"cap_front_width": -1}),
        at("UA_front", {"underarm_height": 1}, {}),
        at("hem_fold_front", {"hem_turnup": 1}, _HEM_FRONT_Y),
        at("hem_front", {}, _HEM_FRONT_Y),
        at("hem_back", {}, _HEM_BACK_Y),
    ),
    ("cubic", "cubic", "cubic", "cubic", "line", "line", "line"),
    ("underarm_wide", "sleeve_cap", "sleeve_cap", "underarm_narrow", "underarm_narrow", "sleeve_hem", "underarm_wide"),
    (NotchRecipe("crown_notch", "cap_crown", "UA_front"),),
    smooth=("cap_crown",),  # the PDS cap is one curve; the crown notch only marks a point on it
)
