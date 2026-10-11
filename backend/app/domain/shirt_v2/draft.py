"""shirt_v2 draft: the demo_v1 piece set and chart reading with the 1078375 Optitex curve shapes, real PDS
notches (yoke shoulder, sleeve crown), a double yoke as on the PDS and grain along collar and band.
"""
import json
from collections.abc import Sequence
from hashlib import sha256

from app.domain.collar_targets import apply_collar_targets
from app.domain.geometry import length, make_piece, unfold
from app.domain.shirt_set import sleeve_and_placket
from app.domain.shirt_v2.body import back_half, front_half, underarm, yoke_half
from app.domain.shirt_v2.curves import simplify
from app.domain.shirt_v2.neck import band, collar, unfold_x
from app.domain.shirt_v2.sleeve import sleeve_outline

PROFILE = "mens_shirt_optitex_curves_v2"


def _piece(name: str, points: list, marks: Sequence = (), quantity: int = 2, fold: bool = False,
           seams: dict | None = None) -> dict:
    """make_piece, with the notches drafted in the outline's coordinates moved into its normalized frame."""
    piece = make_piece(name, points, quantity, fold, seams)
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    piece["notches"] = [[round(x - x0, 6), round(y - y0, 6)] for x, y in marks]
    return piece


def _along(piece: dict) -> dict:
    """Grain along the piece's length (collar and band, as the 1078375 block), centred, half as long."""
    w, h = piece["width"], piece["height"]
    piece["grainline"] = [[w * 0.25, h / 2], [w * 0.75, h / 2]]
    return piece


def pieces(m: dict, back_neck_drop: float) -> list[dict]:
    front, back, yoke = front_half(m), back_half(m), yoke_half(m, back_neck_drop)
    half_neck = length(front["neckline"]) + length(yoke["neckline"])
    band_half, band_top = band(m, half_neck)
    collar_whole = [[-x, -y] for x, y in unfold_x(collar(m, band_top))]  # turned so the outer edge is up
    outline, cap, wrist, _ = sleeve_outline(m)
    outline = simplify(outline, keep=((0, 0),))
    sleeve, placket = sleeve_and_placket(m, outline, cap, wrist)
    sleeve["notches"].append(_piece("Sleeve", outline, [[0, 0]])["notches"][0])  # crown notch
    (x, y), cuff = yoke["notch"], (m["cuff_edge_to_edge"], m["cuff_width"])
    attachment = 2 * half_neck
    return [
        _piece("Front", simplify(front["points"]),
               seams={"armhole": length(front["armhole"]), "neckline": length(front["neckline"])}),
        _piece("Back", simplify(unfold(back["points"])), quantity=1, fold=True, seams={
            "yoke": 2 * back["yoke"], "armhole": length(back["armhole"]) + length(yoke["armhole"])}),
        _piece("Yoke", simplify(unfold(yoke["points"])), [[x, y], [-x, y]], fold=True,
               seams={"yoke": 2 * yoke["yoke"], "neckline": 2 * length(yoke["neckline"])}),
        sleeve,
        apply_collar_targets(_along(_piece("Collar", simplify(collar_whole), seams={"attachment": attachment})),
                             m, attachment),
        _along(_piece("Collar Stand", simplify(unfold_x(band_half)), seams={"attachment": attachment})),
        _piece("Cuff", [[0, 0], [cuff[0], 0], [cuff[0], cuff[1]], [0, cuff[1]]], quantity=4),
        placket,
    ]


def draft_v2(m: dict, size: str, profile) -> dict:
    missing = [k for k in profile.required_measurements if k not in m or m[k] <= 0]
    if missing:
        raise ValueError("Missing positive measurements: " + ", ".join(missing))
    neck, shoulder, chest = m["neck_width"] / 2, m["shoulder_point_to_point"] / 2, m["half_chest"] / 2
    if not 0 < neck < shoulder < chest or not m["shoulder_slope"] < m["yoke_depth_cb"] < \
            underarm(m) < min(m["front_length_hps"], m["back_length_hps"]):
        raise ValueError("Neck, shoulder, chest, yoke and armhole dimensions are incompatible")
    inputs = json.dumps({"measurements": m, "size": size, "profile": PROFILE}, sort_keys=True)
    return {
        "size": size, "profile": PROFILE, "input_hash": sha256(inputs.encode()).hexdigest(),
        "pieces": pieces(m, m.get("back_neck_drop") or profile.back_neck_drop_cm),
        "assumptions": list(profile.assumptions),
        "profile_metadata": {"id": profile.id, "version": profile.version, "garment_family": profile.garment_family,
                             "seam_policy": profile.seam_policy, "validators": profile.validators},
        "measurements": m, "seam_allowance": 0, "schema_version": 1, "calibration": profile.calibration,
    }
