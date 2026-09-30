import json
from hashlib import sha256

from app.domain.back_yoke import back_shoulder_half
from app.domain.catalog import PROFILE
from app.domain.collar_targets import apply_collar_targets
from app.domain.geometry import length, make_piece, unfold
from app.domain.geometry import quadratic as q
from app.domain.profiles import get_profile
from app.domain.shirt_set import sleeve_and_placket


def draft(m: dict[str, float], size: str, profile_id: str = "demo_v1") -> dict:
    profile = get_profile(profile_id)
    missing = [k for k in profile.required_measurements if k not in m or m[k] <= 0]
    if missing:
        raise ValueError("Missing positive measurements: " + ", ".join(missing))
    chest, waist, hip = m["half_chest"] / 2, m["half_waist"] / 2, m["half_bottom_opening"] / 2
    shoulder, neck = m["shoulder_point_to_point"] / 2, m["neck_width"] / 2
    back_sh = back_shoulder_half(shoulder, m)
    slope, depth = m["shoulder_slope"], m["half_armhole_straight"]
    front, back, yoke = m["front_length_hps"], m["back_length_hps"], m["yoke_depth_cb"]
    drop = m["front_neck_drop"]
    if not 0 < neck < back_sh <= shoulder < chest or not slope < yoke < depth < min(front, back):
        raise ValueError("Neck, shoulder, chest, yoke and armhole dimensions are incompatible")
    neckline = q([0, drop], [neck, drop], [neck, 0])
    arm = q([shoulder, slope], [shoulder - 2, depth], [chest, depth])
    front_points = [
        *neckline,
        [shoulder, slope],
        *arm[1:],
        [waist, front * 0.62],
        [hip, front - 2],
        *q([hip, front - 2], [hip * 0.6, front + 1], [0, front])[1:],
    ]
    front_points += [[-m["front_placket_width"], front], [-m["front_placket_width"], drop]]
    back_neck = q([0, profile.back_neck_drop_cm], [neck, profile.back_neck_drop_cm], [neck, 0])
    yoke_half = [*back_neck, [back_sh, slope], [back_sh, yoke], [0, yoke]]
    back_arm = q([back_sh, yoke], [back_sh - 1, depth], [chest, depth])
    back_half = [
        [0, yoke],
        [back_sh, yoke],
        *back_arm[1:],
        [waist, back * 0.62],
        [hip, back - 2],
        *q([hip, back - 2], [hip * 0.6, back + 1], [0, back])[1:],
    ]
    sleeve_len = m["sleeve_length"] - m["cuff_width"]
    cap, bicep, cuff = m["sleeve_cap_height"], m["half_bicep"], m["cuff_edge_to_edge"]
    wrist = cuff + 2 * m.get("sleeve_pleat_depth", 2)
    if sleeve_len <= cap or wrist >= 2 * bicep:
        raise ValueError("Sleeve length/cuff dimensions are incompatible with sleeve cap and bicep")
    cap_curve = [
        *q([-bicep, cap], [-bicep * 0.65, 0], [0, 0]),
        *q([0, 0], [bicep * 0.65, 0], [bicep, cap])[1:],
    ]
    sleeve = [*cap_curve, [wrist / 2, sleeve_len], [-wrist / 2, sleeve_len]]
    neck_length = 2 * (length(neckline) + length(back_neck))
    collar_h, stand_h = m["collar_width_cb"], m["collar_band_width_cb"]
    collar_point = m.get("collar_point", collar_h)
    collar = [
        [0, collar_point],
        [2, 0],
        [neck_length - 2, 0],
        [neck_length, collar_point],
        [neck_length / 2, collar_h],
    ]
    stand = [[0, 0], [neck_length, 0], [neck_length, stand_h], [0, stand_h]]
    sleeve_piece, placket_piece = sleeve_and_placket(m, sleeve, cap_curve, wrist)
    pieces = [
        make_piece("Front", front_points, seams={"armhole": length(arm), "neckline": length(neckline)}),
        make_piece("Back", unfold(back_half), 1, True, {"yoke": 2 * back_sh, "armhole": length(back_arm)}),
        make_piece(
            "Yoke", unfold(yoke_half), 1, True, {"yoke": 2 * back_sh, "neckline": 2 * length(back_neck)}
        ),
        sleeve_piece,
        apply_collar_targets(make_piece("Collar", collar, seams={"attachment": neck_length}), m, neck_length),
        make_piece("Collar Stand", stand, seams={"attachment": neck_length}),
        make_piece("Cuff", [[0, 0], [cuff, 0], [cuff, m["cuff_width"]], [0, m["cuff_width"]]], 4),
        placket_piece,
    ]
    inputs = json.dumps({"measurements": m, "size": size, "profile": PROFILE}, sort_keys=True)
    return {
        "size": size,
        "profile": PROFILE,
        "input_hash": sha256(inputs.encode()).hexdigest(),
        "pieces": pieces,
        "assumptions": list(profile.assumptions),
        "profile_metadata": {"id": profile.id, "version": profile.version,
                             "garment_family": profile.garment_family,
                             "seam_policy": profile.seam_policy, "validators": profile.validators},
        "measurements": m,
        "seam_allowance": 0,
        "schema_version": 1,
        "calibration": profile.calibration,
    }
