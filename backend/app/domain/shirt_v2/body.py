"""shirt_v2 body halves (Front, Back, Yoke) in the demo frame: x across from CF/CB, y down from HPS level.

Points come from the measurement chart exactly as demo_v1 reads it; every curve between them takes its shape
from the matching 1078375 PDS sew-line curve (``curves.py``). Front/back widths split the half-body
measurements in the 1078375 block's own front/back proportion instead of half and half.
The chart's neck width is the yoke's; the front neck sits inside it by the PDS amount (forward shoulder, T147;
how the shoulder seam moves is still open, Q13).
"""
from math import dist, sqrt

from app.domain.back_yoke import back_shoulder_half
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.blocks.shirt.shape import shape
from app.domain.shirt_v2.curves import Pt, cubic, fractions, lerp, square_end

REF = reference_measurements()
CHEST_FRONT = REF["half_chest_front"] / (REF["half_chest_front"] + REF["half_chest_back"])
HEM_FRONT = REF["front_hem_width"] / (REF["front_hem_width"] + REF["back_hem_width"])
HEM_RISE = shape()["FRT"].offsets["side_hem"][0]  # the side hem sits this far above the CF hem (cm)
PLACKET_RISE = REF["placket_rise"]  # grown-on placket top above the CF neck point (cm)
SHOULDER_NOTCH = shape()["back_YK"].notches["shoulder_notch"]
YOKE_INSET = REF["across_back_half"] - REF["yoke_seam_width"]  # yoke seam ends this far inside the SP (cm)
YOKE_DROP = REF["back_yoke_drop"]  # the back yoke seam drops this far toward the armhole (1078375 PDS, T147)
FRONT_NECK_INSET = REF["back_neck_width"] - REF["front_neck_width"]  # front HPS inside the yoke HPS (PDS, T147)


def widths(m: dict, front_share: float, hem_share: float) -> tuple[tuple[float, float, float], ...]:
    """(chest, waist, hem) half widths of the front and of the back half."""
    whole = (m["half_chest"], m["half_waist"], m["half_bottom_opening"])
    front = (whole[0] * front_share, whole[1] * front_share, whole[2] * hem_share)
    return front, tuple(w - f for w, f in zip(whole, front, strict=True))


def underarm(m: dict) -> float:
    """Underarm level below HPS. "1/2 ARMHOLE (STRAIGHT)" is read as the straight line from the front
    shoulder point to the underarm point (demo_v1 reads it as the depth itself, which leaves every armhole
    about 10 cm short of its sleeve cap)."""
    front, _ = widths(m, CHEST_FRONT, HEM_FRONT)
    across = front[0] - m["shoulder_point_to_point"] / 2
    if not 0 < across < m["half_armhole_straight"]:
        raise ValueError("Half armhole (straight) is shorter than the chest reaches past the shoulder point")
    return m["shoulder_slope"] + sqrt(m["half_armhole_straight"] ** 2 - across * across)


def _side(m: dict, length: float, top: Pt, side: tuple[float, float, float]) -> list[Pt]:
    """Armhole bottom → waist (the chart's level) → side hem, straight lines as on the PDS side seams."""
    rise = m.get("hem_curve", HEM_RISE)
    return [top, [side[1], m["waist_position_hps"]], [side[2], length - rise]]


def front_half(m: dict) -> dict:
    neck, drop, ext = m["neck_width"] / 2 - FRONT_NECK_INSET, m["front_neck_drop"], m["front_placket_width"]
    shoulder, slope, depth, length = m["shoulder_point_to_point"] / 2, m["shoulder_slope"], underarm(m), \
        m["front_length_hps"]
    front, _ = widths(m, CHEST_FRONT, HEM_FRONT)
    neckline = cubic([0, drop], [neck, 0], fractions("FRT", "CF_neck:HPS"))
    armhole = cubic([shoulder, slope], [front[0], depth], fractions("FRT", "SP:UA"))
    side = _side(m, length, armhole[-1], front)
    hem = square_end(side[-1], [-ext, length])
    points = [[-ext, drop - PLACKET_RISE], [0, drop - PLACKET_RISE], *neckline, *armhole, *side[1:], *hem[1:]]
    return {"points": points, "armhole": armhole, "neckline": neckline, "shoulder": dist(neckline[-1], armhole[0])}


def back_half(m: dict) -> dict:
    yoke, depth, length = m["yoke_depth_cb"], underarm(m), m["back_length_hps"]
    back_sh = back_shoulder_half(m["shoulder_point_to_point"] / 2, m)
    _, back = widths(m, CHEST_FRONT, HEM_FRONT)
    armhole = cubic([back_sh - YOKE_INSET, yoke + YOKE_DROP], [back[0], depth], fractions("back", "yoke_armhole:UA"))
    side = _side(m, length, armhole[-1], back)
    hem = square_end(side[-1], [0, length])
    return {"points": [[0, yoke], *armhole, *side[1:], *hem[1:]], "armhole": armhole, "yoke": back_sh - YOKE_INSET}


def yoke_half(m: dict, back_neck_drop: float) -> dict:
    neck, slope, yoke = m["neck_width"] / 2, m["shoulder_slope"], m["yoke_depth_cb"]
    back_sh = back_shoulder_half(m["shoulder_point_to_point"] / 2, m)
    neckline = cubic([0, back_neck_drop], [neck, 0], fractions("back_YK", "CB_neck:HPS"))
    armhole = cubic([back_sh, slope], [back_sh - YOKE_INSET, yoke], fractions("back_YK", "SP:yoke_armhole"))
    notch = lerp([neck, 0], [back_sh, slope], SHOULDER_NOTCH)
    return {"points": [*neckline, *armhole, [0, yoke]], "neckline": neckline, "armhole": armhole, "notch": notch,
            "yoke": back_sh - YOKE_INSET, "shoulder": dist(neckline[-1], armhole[0])}
