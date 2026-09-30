"""Seam, inventory, and source-dimension validators."""
from app.domain.back_yoke import back_shoulder_half
from app.domain.tolerances import LENGTH_CM, SLEEVE_EASE_CM, SOURCE_DIMENSION_CM, within_tolerance
from app.infrastructure.pattern_checks import REQUIRED_PIECES


def seam_checks(pattern):
    results = []
    pieces = {p["name"]: p for p in pattern["pieces"]}
    missing = sorted(REQUIRED_PIECES - pieces.keys())
    if missing or len(pieces) != len(pattern["pieces"]):
        return [{"code": "PIECE_INVENTORY", "severity": "ERROR",
                 "message": "Missing or duplicate pieces: " + ", ".join(missing)}]
    checks = [
        ("Yoke seam", pieces["Yoke"]["seams"]["yoke"], pieces["Back"]["seams"]["yoke"], LENGTH_CM),
        ("Collar attachment", pieces["Collar Stand"]["seams"]["attachment"],
         2 * pieces["Front"]["seams"]["neckline"] + pieces["Yoke"]["seams"]["neckline"], LENGTH_CM),
        ("Sleeve cap / armhole", pieces["Sleeve"]["seams"]["cap"],
         pieces["Front"]["seams"]["armhole"] + pieces["Back"]["seams"]["armhole"], SLEEVE_EASE_CM),
    ]
    for name, actual, expected, tolerance in checks:
        results.append({
            "code": "SEAM_CHECK", "name": name,
            "severity": "PASS" if within_tolerance(actual, expected, tolerance) else "WARNING",
            "message": f"{name}: {actual:.2f} cm vs {expected:.2f} cm; tolerance {tolerance} cm",
            "actual": actual, "expected": expected, "tolerance": tolerance,
        })
    measurements = pattern["measurements"]
    dimension_targets = [
        ("Front", "height", "front_length_hps", "Front length"),
        ("Back", "height", "back_length_hps", "Back body length excluding yoke"),
        ("Sleeve", "height", "sleeve_length", "Sleeve body length excluding cuff"),
        ("Cuff", "width", "cuff_edge_to_edge", "Cuff width"),
        ("Cuff", "height", "cuff_width", "Cuff height"),
        ("Yoke", "height", "yoke_depth_cb", "Yoke depth"),
        ("Yoke", "width", "shoulder_point_to_point", "Yoke shoulder span"),
        ("Sleeve Placket", "width", "sleeve_placket_width", "Sleeve placket width"),
        ("Sleeve Placket", "height", "sleeve_placket_length", "Sleeve placket length"),
    ]
    for piece_name, dimension, key, label in dimension_targets:
        if key not in measurements or piece_name not in pieces:
            continue
        actual = pieces[piece_name][dimension]
        expected = measurements[key]
        source_keys = [key]
        adjustment = {"Back": "yoke_depth_cb", "Sleeve": "cuff_width"}.get(piece_name)
        if adjustment:
            if adjustment not in measurements:
                continue
            expected -= measurements[adjustment]
            source_keys.append(adjustment)
        if piece_name == "Yoke" and dimension == "width":
            expected = 2 * back_shoulder_half(expected / 2, measurements)
            source_keys.extend(["forward_shoulder_neck", "forward_shoulder_armhole"])
        results.append({
            "code": "DIMENSION_CHECK", "piece": piece_name,
            "severity": "PASS" if within_tolerance(actual, expected, SOURCE_DIMENSION_CM) else "WARNING",
            "actual": actual, "expected": expected, "tolerance": SOURCE_DIMENSION_CM,
            "source_keys": source_keys,
            "message": f"{label}: {actual:.2f} cm vs source {expected:.2f} cm",
        })
    for key, factor, label in [
        ("collar_buttoned_length", 2, "Buttoned collar length"),
        ("collar_outside_edge", 1, "Collar outside edge"),
    ]:
        if key not in measurements:
            continue
        actual = pieces["Collar Stand"]["seams"]["attachment"] if factor == 2 else pieces["Collar"]["width"]
        expected = measurements[key] * factor
        results.append({
            "code": "COLLAR_SOURCE_CHECK",
            "severity": "PASS" if within_tolerance(actual, expected, SOURCE_DIMENSION_CM) else "WARNING",
            "actual": actual, "expected": expected, "piece": "Collar",
            "message": f"{label}: demo span {actual:.2f} cm vs source {expected:.2f} cm. Calibrate before cutting.",
        })
    results.append({
        "code": "DEMO_CALIBRATION", "severity": "WARNING",
        "message": "Demo drafting profile. Production calibration and physical fit validation are required.",
    })
    return results
