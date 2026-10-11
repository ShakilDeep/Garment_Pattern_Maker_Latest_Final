"""Measurement charts that describe the client's 1078375 PDS at size L in shirt_v2's reading of a chart.

The PDS has no chart, so each value is derived from its sew-line measurements (``measurements_1078375_L``).
Its front hangs from the front's own (forward-shoulder) HPS and its yoke from the yoke's, which one shirt_v2
chart cannot hold at once, so there is a chart per frame: ``front`` for FRT, ``back`` for back and back YK.
"""
from math import hypot

from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.shirt_v2.body import CHEST_FRONT, HEM_RISE

R = reference_measurements()
HALF_CHEST = R["half_chest_front"] + R["half_chest_back"]
WAIST_AT = 48.0  # any level on the straight PDS side seam


def _common(neck_half: float, shoulder_half: float, slope: float, underarm: float, length: float) -> dict:
    across = R["half_chest_front"] - shoulder_half
    side_hem_y = length - HEM_RISE
    share = (WAIST_AT - underarm) / (side_hem_y - underarm)
    waist_front = R["half_chest_front"] + share * (R["front_hem_width"] - R["half_chest_front"])
    return {
        "neck_width": 2 * neck_half, "shoulder_point_to_point": 2 * shoulder_half, "shoulder_slope": slope,
        "half_armhole_straight": hypot(across, underarm - slope), "half_chest": HALF_CHEST,
        "half_waist": waist_front / CHEST_FRONT, "waist_position_hps": WAIST_AT,
        "half_bottom_opening": R["front_hem_width"] + R["back_hem_width"], "hem_curve": HEM_RISE,
        "front_neck_drop": R["front_neck_drop"], "front_placket_width": R["front_extension"],
        "collar_width_cb": R["collar_width_cb"], "collar_band_width_cb": R["band_height_cb"],
        "half_bicep": R["bicep"] / 2, "sleeve_cap_height": R["cap_height"],
        "sleeve_length": 60.0, "cuff_width": 6.0, "cuff_edge_to_edge": 25.0, "sleeve_pleat_depth": 2.0,
        "sleeve_placket_length": 14.0, "sleeve_placket_width": 2.5,
        "forward_shoulder_neck": 0.0, "forward_shoulder_armhole": 0.0,
    }


def front() -> dict:
    underarm = R["front_shoulder_drop"] + R["front_armhole_depth"]
    chart = _common(R["front_neck_width"], R["front_neck_width"] + R["front_shoulder_width"],
                    R["front_shoulder_drop"], underarm, R["front_length"])
    yoke = R["yoke_depth_cb"] + R["back_neck_rise"]
    return {**chart, "front_length_hps": R["front_length"], "back_length_hps": R["front_length"] + 5,
            "yoke_depth_cb": min(yoke, underarm - 1), "back_neck_drop": R["back_neck_rise"]}


def back() -> dict:
    yoke = R["yoke_depth_cb"] + R["back_neck_rise"]
    underarm = yoke + R["back_yoke_drop"] + R["back_armhole_depth"]
    length = yoke + R["back_length"]
    chart = _common(R["back_neck_width"], R["across_back_half"], R["yoke_shoulder_drop"], underarm, length)
    return {**chart, "front_length_hps": length, "back_length_hps": length, "yoke_depth_cb": yoke,
            "back_neck_drop": R["back_neck_rise"]}
